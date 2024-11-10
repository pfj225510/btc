import asyncio
import queue
import time
import json
from datetime import datetime, timedelta

import requests
from binance.client import Client
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient
from wei import send_wechat_message
import threading

# 设置API密钥和秘密
with open('luna_id.json', 'r') as file:
    data = json.load(file)
    api_key = data["api_key"]
    api_secret = data["api_secret"]

# 创建币安客户端
client = Client(api_key, api_secret)

# 全局变量，用于存储上一次接收到的BTC价格
last_btc_price = None
usdt_balance = 1
last_message = []
purchase_cost = 7.42
stop_threads = False  # 用于控制线程停止的信号
last_sell_price = 68009

# 获取当前时间
now = datetime.now()

# 获取半个小时前的时间
half_hour_ago = now - timedelta(minutes=1440)

las_sell_time = half_hour_ago
need_sell = False
current_LUNC_value = 1
PRICE_THRESHOLD = 0.0005  # 假设价格波动小于这个值时忽略
LUNC_balance = 1
LUNC_price = 1
# 初始化变量
last_price = None
trend = None
lowest_price = None
highest_price = None
low_timing = datetime.now()
hign_timing = datetime.now()
# def sq(_, message):
#     q.put(message)
lowest24_price = None
minu_hign = None
minu_low = None
def get_price_minu(minu):

    highest_price = None
    lowest_price = None
    dt = datetime.now()
    if dt.minute % 5 == 0 and dt.second == 0 or minu_low is None:
        # Binance API的K线数据接口
        url = "https://api.binance.com/api/v3/klines"

        # 请求参数
        params = {
            'symbol': 'BTCUSDT',    # 交易对，BTCUSDT表示比特币兑美元
            'interval': '1m',       # 时间间隔，1m表示1分钟的K线
            'limit': 60 * minu            # 获取最近60条数据，代表最近1小时（60分钟）
        }

        # 发起请求获取数据
        response = requests.get(url, params=params)

        # 将数据转换为JSON格式
        data = response.json()

        # 初始化最高价和最低价
        highest_price = -float('inf')  # 负无穷大
        lowest_price = float('inf')    # 正无穷大

        # 遍历每一分钟的数据
        for kline in data:
            high_price = float(kline[2])  # K线数据的第3个元素是最高价
            low_price = float(kline[3])   # K线数据的第4个元素是最低价

            # 更新最高价和最低价
            if high_price > highest_price:
                highest_price = high_price
            if low_price < lowest_price:
                lowest_price = low_price

        # 输出最近1小时内的最高价和最低价
    return highest_price,lowest_price


def get_binance_btc_price():
    # url = "https://api.binance.com/api/v3/ticker/price"
    # params = {'symbol': 'BTCUSDT'}
    global lowest24_price, hiest24_price, minu_hign, minu_low

    try:
        # response = requests.get(url, params=params)
        # data = response.json()
        # price = data['price']

        # 获取账户中可用的USDT余额
        account_info = client.get_account()
        usdt_balance = None
        LUNC_balance = None
        for asset in account_info['balances']:
            if asset['asset'] == 'USDT':
                usdt_balance = float(asset['free'])
            elif asset['asset'] == type:
                LUNC_balance = float(asset['free'])
            if usdt_balance is not None and LUNC_balance is not None:
                break

        LUNC_ticker = client.get_symbol_ticker(symbol=f"{type}USDT")

        dt = datetime.now()
        if dt.minute % 5 == 0 and dt.second == 0 or lowest24_price is None:
            url = "https://api.binance.com/api/v3/ticker/24hr"
            params = {
                'symbol': 'BTCUSDT'  # 获取BTC对USDT的交易对数据
            }

            response = requests.get(url, params=params)

            # 检查API请求是否成功
            if response.status_code != 200:
                print(f"API请求失败，状态码: {response.status_code}")

            data = response.json()
            # 提取24小时内最低价
            lowest24_price = round(float(data['lowPrice']), 2)
            hiest24_price = round(float(data['highPrice']), 2)

        minu_hign_t, minu_low_t = get_price_minu(5)
        if minu_hign_t:
            minu_hign = minu_hign_t
            minu_low = minu_low_t

        return usdt_balance, LUNC_ticker, LUNC_balance


    except Exception as e:
        print(f"获取比特币价格时出错: {e}")
        return None


def set_btc():
    global last_btc_price
    global usdt_balance
    global LUNC_balance
    global LUNC_price
    global current_LUNC_value
    global need_sell


    while not stop_threads:
        price = get_binance_btc_price()
        if price is not None:
            # last_btc_price = price[0]
            usdt_balance = price[0]
            LUNC_ticker = price[1]
            LUNC_balance = price[2]
            LUNC_price = float(LUNC_ticker['price'])
            current_LUNC_value = round(LUNC_balance * LUNC_price, 2)
            if current_LUNC_value < purchase_cost * 0.99:
                need_sell = True
            else:
                need_sell = False

        else:
            last_btc_price = None

        time.sleep(1)  # 等待5秒钟


def message_handler(_, message):
    global last_price, trend, lowest_price, highest_price, last_sell_price, stop_threads, low_timing, hign_timing

    data = json.loads(message)
    price = data.get('p')  # 从 WebSocket 数据中提取价格
    if price is None:
        return
    else:
        price = float(price)

    if last_price is None:
        last_price = price
        lowest_price = price
        highest_price = price
        print(f"Initial price: {price}")
        return

    price_change = (price - last_price) / last_price

    if abs(price_change) < PRICE_THRESHOLD:
        # 忽略噪音
        return

    if price > last_price:
        # 价格上涨
        now = datetime.now()
        if trend != 'up':
            # 如果之前不是上涨趋势，重置最低价格
            lowest_price = last_price
            hign_timing = datetime.now()

            # print(f"Trend reversed to up: Last Decrease: {(highest_price - lowest_price) / highest_price * 100:.6f}%")

        trend = 'up'
        highest_price = price  # 更新最高点

        # 计算从最低点到当前价格的涨幅
        increase_percentage = (price - lowest_price) / lowest_price * 100
        # print(
        #     f"Price rising: Lowest Price: {lowest_price}, Current Price: {price}, Increase: {increase_percentage:.6f}%")
        print(
            f"{now} Current Price: {price:.2f},last_sell_price:{last_sell_price:.2f},{minu_low} ↗: {increase_percentage:.6f}%，usd余额: ${round(usdt_balance, 2)}， "
            f"doge个数: {int(LUNC_balance)}, doge市值{current_LUNC_value}，买入成本{purchase_cost}")
        if (now - hign_timing).total_seconds() > 14:
            print('超过5秒价格没突破，更新低点')
            lowest_price = price
            hign_timing = datetime.now()
        else:
            cur_time = datetime.now()
            time_diff = (cur_time - las_sell_time).total_seconds() / 60
            if 0.2 > increase_percentage > 0.1 and time_diff > 2:
                if lowest_price < minu_low and (price < last_sell_price) and time_diff > 60:
                    buy()
                    send_wechat_message(f"2BTC Price increased {increase_percentage:.1f}%,  Buying doge,  "
                                        f"Previous Price: {lowest_price}, Current Price: {int(price)}")
                else:
                    send_wechat_message(f"2BTC Price increased {increase_percentage:.1f}%,  暂时不买,  "
                                        f"Previous Price: {lowest_price}, Current Price: {int(price)}")

            elif 0.5 > increase_percentage > 0.2:
                if price < last_sell_price or price < lowest24_price or time_diff > 1440:
                    buy()
                    send_wechat_message(f"2BTC Price increased {increase_percentage:.1f}%,  Buying doge,  "
                                        f"Previous Price: {lowest_price}, Current Price: {int(price)}")
                else:

                    send_wechat_message(f"2BTC Price increased {increase_percentage:.1f}%,  暂时不买,  "
                                        f"Previous Price: {lowest_price}, Current Price: {int(price)}")

            elif 1 > increase_percentage > 0.5:

                cur_time = datetime.now()
                time_diff = (cur_time - las_sell_time).total_seconds() / 60
                if time_diff > 1440 or price < last_sell_price:
                    buy()
                    send_wechat_message(f"2BTC Price increased {increase_percentage:.1f}%,  Buying doge,  "
                                        f"Previous Price: {lowest_price}, Current Price: {int(price)}")
                else:
                    send_wechat_message(f"2BTC Price increased {increase_percentage:.1f}%,  暂时不买,  "
                                        f"Previous Price: {lowest_price}, Current Price: {int(price)}")

            elif increase_percentage > 1:
                cur_time = datetime.now()
                time_diff = (cur_time - las_sell_time).total_seconds() / 60
                if time_diff > 60:
                    buy()
                    send_wechat_message(f"2BTC Price increased {increase_percentage:.1f}%,  Buying doge,  "
                                        f"Previous Price: {lowest_price}, Current Price: {int(price)}")
                else:
                    send_wechat_message(f"2BTC Price increased {increase_percentage:.1f}%,  暂时不买,  "
                                        f"Previous Price: {lowest_price}, Current Price: {int(price)}")


    elif price < last_price:
        # 价格下跌
        now = datetime.now()
        if trend != 'down':
            # 如果之前不是下降趋势，重置最高价格
            highest_price = last_price
            low_timing = datetime.now()

            # print(f"Trend reversed to down: Last Increase: {(highest_price - lowest_price) / lowest_price * 100:.6f}%")

        trend = 'down'
        lowest_price = price  # 更新最低点

        # 计算从最高点到当前价格的跌幅
        decrease_percentage = (highest_price - price) / highest_price * 100
        # print(
        #     f"Price falling: Highest Price: {highest_price}, Current Price: {price}, Decrease: {decrease_percentage:.6f}%")
        print(
            f"{now} Current Price: {price:.2f},last_sell_price:{last_sell_price:.2f},{minu_hign} ↘: {decrease_percentage:.6f}%, usd余额: ${round(usdt_balance, 2)}， "
            f"doge个数: {int(LUNC_balance)}, doge市值{current_LUNC_value}，买入成本{purchase_cost}")


        if (now - low_timing).total_seconds() > 14:
            print('超过5秒价格没突破，更新高点')
            highest_price = price
            low_timing = datetime.now()
        else:
            if -0.2 <= -decrease_percentage <= -0.1:
                # 如果当前市值高于购买成本，全部卖出
                send_wechat_message('mai')
                if (current_LUNC_value - purchase_cost) / purchase_cost * 100 > 0.1 and price > minu_hign:
                    if current_LUNC_value > 1:
                        sell()
                        last_sell_price = price
                        send_wechat_message(f"2BTC Price decreased  {decrease_percentage:1f}% ,  Selling doge"
                                            f"Previous Price: {highest_price}, Current Price: {price}")
                else:
                    send_wechat_message(f"2BTC Price decreased  {decrease_percentage:1f}% ,"
                                        f"Previous Price: {highest_price}, Current Price: {price}")
            if -0.3 <= -decrease_percentage <= -0.2:
                # 如果当前市值高于购买成本，全部卖出
                send_wechat_message('mai')
                if (current_LUNC_value - purchase_cost) / purchase_cost * 100 > 0.1 or need_sell or price > hiest24_price:
                    if current_LUNC_value > 1:
                        sell()
                        last_sell_price = price
                        send_wechat_message(f"2BTC Price decreased  {decrease_percentage:1f}% ,  Selling doge"
                                            f"Previous Price: {highest_price}, Current Price: {price}")
                else:
                    send_wechat_message(f"2BTC Price decreased  {decrease_percentage:1f}% ,"
                                        f"Previous Price: {highest_price}, Current Price: {price}")
            elif -0.4 <= -decrease_percentage <= -0.3:
                # 如果当前市值高于购买成本，全部卖出
                if (current_LUNC_value - purchase_cost) / purchase_cost * 100 > 0.05 or need_sell:
                    if current_LUNC_value > 1:
                        sell()
                        last_sell_price = price
                        send_wechat_message(f"2BTC Price decreased  {decrease_percentage:1f}% ,  Selling doge"
                                            f"Previous Price: {highest_price}, Current Price: {price}")
                else:
                    send_wechat_message(f"2BTC Price decreased  {decrease_percentage:1f}% ,"
                                        f"Previous Price: {highest_price}, Current Price: {price}")

            elif -0.6 < -decrease_percentage < -0.4:
                # 如果当前市值高于购买成本，全部卖出
                if (current_LUNC_value - purchase_cost) / purchase_cost * 100 > 0.1 or need_sell:
                    if current_LUNC_value > 1:
                        sell()
                        last_sell_price = price
                        send_wechat_message(f"2BTC Price decreased  {decrease_percentage:1f}% ,  Selling doge"
                                            f"Previous Price: {highest_price}, Current Price: {price}")
                else:
                    send_wechat_message(f"2BTC Price decreased  {decrease_percentage:1f}% ,"
                                        f"Previous Price: {highest_price}, Current Price: {price}")
            elif -decrease_percentage < -1:
                if current_LUNC_value > 1:
                    sell()
                stop_threads = True

                send_wechat_message(f"2 砸盘 BTC Price decreased  {decrease_percentage:.1f}% ,"
                                    f"Previous Price: {highest_price}, Current Price: {price}")

    last_price = price


def buy():
    try:
        global purchase_cost

        if usdt_balance and usdt_balance > 5:  # 确保有足够的资金且大于最低交易金额
            # 获取当前LUNC的市场价格

            # 计算可以买入的LUNC数量
            quantity = (usdt_balance / LUNC_price) * 0.99

            # 下达买入订单
            order = client.order_market_buy(
                symbol=f'{type}USDT',
                quantity=int(quantity)  # LUNC通常没有小数位
            )
            purchase_cost = usdt_balance

            send_wechat_message(f"usd余额{usdt_balance},  可买入{quantity}个{type}")

            order_id = order['orderId']
            start_time = time.time()
            timeout_seconds = 10

            while True:
                time.sleep(0.3)  # 每 10 秒检查一次

                # 获取订单状态
                order_status = client.get_order(symbol=f'{type}USDT', orderId=order_id)

                # 检查订单状态是否已成交
                if order_status['status'] == 'FILLED':
                    cummulativeQuoteQty = round(float(order.get('cummulativeQuoteQty')), 2)
                    executedQty = round(float(order.get('executedQty')), 2)
                    purchase_cost = cummulativeQuoteQty

                    send_wechat_message(f"Order has been filled. ${cummulativeQuoteQty} 买了{executedQty} 个{type}")
                    # send_wechat_message(f'{order_status}')
                    break

                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    client.cancel_order(symbol=f'{type}USDT', orderId=order_id)
                    send_wechat_message("Order cancelled due to timeout.")
                    break


        else:
            # send_wechat_message(f"Insufficient USDT balance or below minimum trading amount:{usdt_balance}.")
            pass
    except Exception as e:
        send_wechat_message(f"An error occurred while buying {type}: {e}")


def sell():
    global las_sell_time
    try:
        global purchase_cost

        if LUNC_balance and LUNC_balance > 100:  # 确保有足够的LUNC且大于最低交易数量
            # 下达卖出订单

            order = client.order_market_sell(
                symbol=f'{type}USDT',
                quantity=int(LUNC_balance)  # LUNC通常没有小数位

            )
            las_sell_time = datetime.now()
            send_wechat_message(f"{type}余额{LUNC_balance}g个,  全卖了")

            order_id = order['orderId']
            start_time = time.time()
            timeout_seconds = 10

            while True:
                time.sleep(1)  # 每 10 秒检查一次

                # 获取订单状态
                order_status = client.get_order(symbol=f'{type}USDT', orderId=order_id)

                # 检查订单状态是否已成交
                if order_status['status'] == 'FILLED':
                    cummulativeQuoteQty = round(float(order.get('cummulativeQuoteQty')), 6)
                    executedQty = round(float(order.get('executedQty')), 6)

                    beni = cummulativeQuoteQty - purchase_cost

                    send_wechat_message(
                        f"Order has been filled. {executedQty} 个{type}卖了 ${cummulativeQuoteQty}, 收益是{beni}")
                    # send_wechat_message(f'{order_status}')

                    break

                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    client.cancel_order(symbol=f'{type}USDT', orderId=order_id)
                    send_wechat_message("Order cancelled due to timeout.")
                    break


        else:
            # send_wechat_message("Insufficient LUNC balance or below minimum trading amount.")
            pass
    except Exception as e:
        send_wechat_message(f"An error occurred while selling {type}: {e}")


def on_error(_, exception):
    print(f"An error occurred: {exception}")


def close_handler(_, message):
    print(f'close{message}')


def start_websocket():
    global stop_threads
    stop_threads = False  # 用于控制线程停止的信号

    try:

        global my_client
        proxies = {'http': 'http://127.0.0.1:33210', 'https': 'http://127.0.0.1:33210', }

        # 创建WebSocket客户端实例
        my_client = SpotWebsocketStreamClient(on_message=message_handler, on_error=on_error, on_close=close_handler)

        # 订阅BTC/USDT的聚合交易流
        my_client.agg_trade(symbol="btcusdt")
        set_btc_thread = threading.Thread(target=set_btc)
        set_btc_thread.start()
        # 创建消费者线程

        while True:
            time.sleep(10)  # check every ten seconds if the websocket is alive
            if not my_client.socket_manager.is_alive():
                raise Exception("WebSocket connection is not alive")


    except Exception as e:
        send_wechat_message(f"Connection failed: {e}")
    finally:
        # 请求停止所有线程
        stop_threads = True

        # 停止WebSocket客户端
        my_client.stop()
        print('Websocket closed')

        # 等待所有线程结束
        set_btc_thread.join()
        print('set_btc_thread closed')
        stop_threads = False  # 用于控制线程停止的信号

# 主函数
if __name__ == "__main__":
    while True:
        last_btc_price = None
        q = queue.Queue()
        type = "LUNC"

        try:
            print('start_websocket启动')
            start_websocket()

        except KeyboardInterrupt:
            send_wechat_message("Program interrupted by user. Exiting...")
            break
        except SystemExit:
            send_wechat_message("System exit called. Exiting...")
            break
        except Exception as e:
            send_wechat_message(f"Error: {e}")
            send_wechat_message("Reconnecting in 10 seconds...")
            time.sleep(10)
