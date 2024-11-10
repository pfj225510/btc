import queue
import time
import json
from datetime import datetime, timedelta

import requests
from binance.client import Client
from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient
from wei_eth import send_wechat_message
import threading
from decimal import Decimal, ROUND_DOWN

# 设置API密钥和秘密
with open('main_id.json', 'r') as file:
    data = json.load(file)
    api_key = data["api_key"]
    api_secret = data["api_secret"]

# 创建币安客户端
client = Client(api_key, api_secret)

# 全局变量，用于存储上一次接收到的BTC价格
last_btc_price = None
usdt_balance = None
last_message = []
purchase_cost = 138
stop_threads = False  # 用于控制线程停止的信号
last_sell_price = 69336
# 获取当前时间
now = datetime.now()

# 获取半个小时前的时间
half_hour_ago = now - timedelta(minutes=1200)

las_sell_time = half_hour_ago
buy_time = half_hour_ago
need_sell = False
import loga

lowest_price = None
hiest_price = None
open_price = None

# def sq(_, message):
#     q.put(message)
type_b = 'BNB'
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
            'symbol': 'BTCUSDT',  # 交易对，BTCUSDT表示比特币兑美元
            'interval': '1m',  # 时间间隔，1m表示1分钟的K线
            'limit': 60 * minu  # 获取最近60条数据，代表最近1小时（60分钟）
        }

        # 发起请求获取数据
        response = requests.get(url, params=params)

        # 将数据转换为JSON格式
        data = response.json()

        # 初始化最高价和最低价
        highest_price = -float('inf')  # 负无穷大
        lowest_price = float('inf')  # 正无穷大

        # 遍历每一分钟的数据
        for kline in data:
            high_price = float(kline[2])  # K线数据的第3个元素是最高价
            low_price = float(kline[3])  # K线数据的第4个元素是最低价

            # 更新最高价和最低价
            if high_price > highest_price:
                highest_price = high_price
            if low_price < lowest_price:
                lowest_price = low_price

        # 输出最近1小时内的最高价和最低价
    return highest_price, lowest_price


def get_binance_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price"
    params = {'symbol': 'BTCUSDT'}
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        price = float(data['price'])
        q.put(price)
        if q.qsize() > 4:
            btc_price = q.get()
        else:
            btc_price = None

        # 获取账户中可用的USDT余额
        account_info = client.get_account()
        usdt_balance = None
        doge_balance = None
        for asset in account_info['balances']:
            if asset['asset'] == 'USDT':
                usdt_balance = float(asset['free'])
            elif asset['asset'] == f'{type_b}':
                doge_balance = float(asset['free'])
            if usdt_balance is not None and doge_balance is not None:
                break

        E_ticker = client.get_symbol_ticker(symbol=f"{type_b}USDT")

        return [btc_price, usdt_balance, E_ticker, doge_balance]


    except Exception as e:
        print(f"获取比特币价格时出错: {e}")
        q.put(None)
        if q.qsize() > 4:
            btc_price = q.get()
        else:
            btc_price = None
        return None


def set_btc():
    global last_btc_price, usdt_balance, doge_balance, doge_price, current_doge_value, need_sell, lowest_price, hiest_price, open_priceminu_hign, minu_low, minu_hign

    while not stop_threads:
        try:
            price = get_binance_btc_price()
            if price is not None:
                last_btc_price = price[0]
                usdt_balance = price[1]
                ETH_ticker = price[2]
                doge_balance = float(price[3])
                doge_price = float(ETH_ticker['price'])
                current_doge_value = round(doge_balance * doge_price, 5)
                if current_doge_value < purchase_cost * 0.985:
                    need_sell = True
                else:
                    need_sell = False
                dt = datetime.now()
                if dt.minute % 10 == 0 and dt.second == 0 or lowest_price is None:
                    try:

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
                        lowest_price = round(float(data['lowPrice']), 2)
                        hiest_price = round(float(data['highPrice']), 2)
                        open_price = round(float(data['openPrice']), 2)

                    except Exception:
                        pass
                minu_hign_t, minu_low_t = get_price_minu(5)
                if minu_hign_t:
                    minu_hign = minu_hign_t
                    minu_low = minu_low_t
                ben_rate = (current_doge_value - purchase_cost) / purchase_cost * 100
                print(
                    f"{dt.strftime('%Y-%m-%d %H:%M:%S')}当前价格: {last_btc_price},上次卖价{last_sell_price},24最低价{lowest_price},{minu_low},24最高价{hiest_price},{minu_hign}usd余额:{round(usdt_balance, 2)},"
                    f"{type_b}个数: {doge_balance:.5f},{type_b}市值{int(current_doge_value)}，成本{int(purchase_cost)}收益率{ben_rate:.2f}")
                loga.log(
                    f"当前价格: {last_btc_price},上次卖价{last_sell_price},24最低价{lowest_price},{minu_low},24最高价{hiest_price},{minu_hign}, 卖出时间{las_sell_time} usd余额: ${round(usdt_balance, 2)},"
                    f" {type_b}个数: {doge_balance:.5f}, {type_b}市值{current_doge_value}，成本{purchase_cost}")
            else:
                last_btc_price = None

            time.sleep(1)  # 等待5秒钟
        except Exception as e:
            print(f'{e}')


def message_handler(_, message):
    global last_btc_price
    global last_sell_price
    global stop_threads

    try:

        # 将消息从JSON字符串解析为Python字典
        data = json.loads(message)
        # loga.log(message)1

        # 提取当前BTC价格
        current_btc_price_str = data.get('p')
        # if current_btc_price_str is None:
        #     return
        current_btc_price = float(current_btc_price_str)

        if last_btc_price is not None and not stop_threads:
            # 计算BTC价格涨跌幅百分比
            price_change_percent = (current_btc_price - last_btc_price) / last_btc_price * 100
            price_change_percent = Decimal(price_change_percent).quantize(Decimal('0.01'), rounding=ROUND_DOWN)  # 截断为4位小数
            cur_time = datetime.now()
            time_diff = (cur_time - las_sell_time).total_seconds() / 60
            buy_time_diff = (cur_time - buy_time).total_seconds() / 60
            if price_change_percent > 0.1 and int(usdt_balance) > 3 and time_diff > 5:
                if 0.2 > price_change_percent > 0.15:
                    if last_btc_price < lowest_price and (current_btc_price < last_sell_price or time_diff > 1440):
                        buy_doge()
                        print(
                            f' buy_doge{last_btc_price},  {current_btc_price},  percent={price_change_percent:.2f}')
                        send_wechat_message(f"BTC Price increased {price_change_percent:.1f}%,  Buying {type_b},  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                    else:
                        send_wechat_message(f"BTC Price increased {price_change_percent:.1f}%,  暂时不买,  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                elif 0.3 > price_change_percent > 0.2:
                    if (last_btc_price < minu_low and current_btc_price < last_sell_price) and time_diff > 30:
                        buy_doge()
                        print(
                            f' buy_doge{last_btc_price},  {current_btc_price},  percent={price_change_percent:.2f}')
                        send_wechat_message(f"BTC Price increased {price_change_percent:.1f}%,  Buying {type_b},  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                    else:
                        send_wechat_message(f"BTC Price increased {price_change_percent:.1f}%,  暂时不买,  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                elif 0.5 > price_change_percent > 0.3:
                    if current_btc_price < last_sell_price or last_btc_price < lowest_price:
                        buy_doge()
                        print(
                            f' buy_eth{last_btc_price},  {current_btc_price},  percent={price_change_percent:.2f}')
                        send_wechat_message(f"BTC Price increased {price_change_percent:.1f}%,  Buying {type_b},  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                    else:
                        send_wechat_message(f"BTC Price increased {price_change_percent:.1f}%,  暂时不买,  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                elif 1 > price_change_percent > 0.5:
                    cur_time = datetime.now()
                    time_diff = (cur_time - las_sell_time).total_seconds() / 60
                    if time_diff > 1440 or current_btc_price < last_sell_price:

                        buy_doge()
                        print(
                            f' buy_eth{last_btc_price},  {current_btc_price},  percent={price_change_percent:.2f}')

                        send_wechat_message(f"BTC Price increased {price_change_percent:.1f}%,  Buying {type_b},  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                    else:
                        send_wechat_message(f"BTC Price increased {price_change_percent:.1f}%,  暂时不买,  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                elif price_change_percent > 1:
                    cur_time = datetime.now()
                    time_diff = (cur_time - las_sell_time).total_seconds() / 60

                    if time_diff > 60:
                        buy_doge()
                        print(f' buy_eth{last_btc_price},  {current_btc_price},  percent={price_change_percent}')

                        send_wechat_message(f"BTC Price increased {price_change_percent}%,  Buying {type_b},  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")
                    else:
                        send_wechat_message(f"BTC Price increased {price_change_percent}%,  暂时不买,  "
                                            f"Previous Price: {last_btc_price}, Current Price: {int(current_btc_price)}")

            elif price_change_percent < -0.1 and current_doge_value > 3:

                if -0.2 < price_change_percent < -0.1:
                    # 如果当前市值高于购买成本，全部卖出
                    if current_btc_price > minu_hign and current_doge_value > purchase_cost :
                        sell_doge()
                        last_sell_price = current_btc_price
                        send_wechat_message(f"BTC Price decreased  {price_change_percent:1f}% ,  Selling {type_b}"
                                            f"Previous Price: {last_btc_price}, Current Price: {current_btc_price}")

                        print(
                            f'sell{last_btc_price},  {current_btc_price},  percent={price_change_percent:.6f}')
                    else:
                        send_wechat_message(
                            f"跌幅 {price_change_percent:.1f}，暂时不卖。Previous Price: {last_btc_price}, Current Price: {current_btc_price} doge市值{int(current_doge_value)}，买入成本{purchase_cost}")

                elif -0.3 < price_change_percent < -0.2:
                    # 如果当前市值高于购买成本，全部卖出
                    b = (current_doge_value - purchase_cost) / purchase_cost * 100
                    if current_btc_price > minu_hign and current_doge_value > purchase_cost or need_sell:
                        sell_doge()
                        last_sell_price = current_btc_price
                        send_wechat_message(f"BTC Price decreased  {price_change_percent:.1f}% ,{b}  Selling {type_b}"
                                            f"Previous Price: {last_btc_price}, Current Price: {current_btc_price}")
                        print(
                            f'sell{last_btc_price},  {current_btc_price},  percent={price_change_percent:.6f}')
                    else:
                        send_wechat_message(
                            f"跌幅 {price_change_percent:.1f}，暂时不卖 {b}。Previous Price: {last_btc_price}, Current Price: {current_btc_price} {type_b}市值{int(current_doge_value)}，买入成本{purchase_cost}")
                elif -0.4 < price_change_percent < -0.3:
                    # 如果当前市值高于购买成本，全部卖出
                    if current_doge_value > purchase_cost or need_sell:
                        sell_doge()
                        last_sell_price = current_btc_price
                        send_wechat_message(f"BTC Price decreased  {price_change_percent:.1f}% ,  Selling {type_b}"
                                            f"Previous Price: {last_btc_price}, Current Price: {current_btc_price}")

                        print(
                            f'sell{last_btc_price},  {current_btc_price},  percent={price_change_percent:.6f}')
                    else:
                        send_wechat_message(
                            f"跌幅 {price_change_percent:.1f}，暂时不卖。Previous Price: {last_btc_price}, Current Price: {current_btc_price} {type_b}市值{int(current_doge_value)}，买入成本{purchase_cost}")
                elif -0.6 < price_change_percent < -0.4:
                    # 如果当前市值高于购买成本，全部卖出
                    if (current_doge_value - purchase_cost) / purchase_cost * 100 > 0.1 or need_sell:
                        sell_doge()
                        last_sell_price = current_btc_price
                        send_wechat_message(f"BTC Price decreased  {price_change_percent:.1f}% ,  Selling {type_b}"
                                            f"Previous Price: {last_btc_price}, Current Price: {current_btc_price}")

                        print(
                            f'sell_eth{last_btc_price},  {current_btc_price},  percent={price_change_percent:.6f}')
                    else:
                        send_wechat_message(
                            f"跌幅 {price_change_percent:.1f}，暂时不卖。Previous Price: {last_btc_price}, Current Price: {current_btc_price} {type_b}市值{int(current_doge_value)}，买入成本{purchase_cost}")
                elif -1 < price_change_percent < -0.6:
                    sell_doge()
                    last_sell_price = current_btc_price

                    print(
                        f'sell{last_btc_price},  {current_btc_price},  percent={price_change_percent:.1f}')

                    send_wechat_message(f"BTC Price decreased  {price_change_percent:.1f}% ,  Selling {type_b}"
                                        f"Previous Price: {last_btc_price}, Current Price: {current_btc_price}")
                elif price_change_percent < -1:
                    if current_doge_value > 1:
                        sell_doge()
                    stop_threads = True

                    send_wechat_message(f"2 砸盘 BTC Price decreased  {price_change_percent:.1f}% ,"
                                        f"Previous Price: {last_btc_price}, Current Price: {current_btc_price}")




    except Exception as e1:
        send_wechat_message(f"Error processing message: {e1}")


def buy_doge():
    try:
        global purchase_cost
        global buy_time

        if usdt_balance and usdt_balance > 1:  # 确保有足够的资金且大于最低交易金额
            # 获取当前DOGE的市场价格

            # 计算可以买入的DOGE数量
            quantity = Decimal((usdt_balance / doge_price) * 0.998).quantize(Decimal('0.001'), rounding=ROUND_DOWN)  # 截断为4位小数
            # 下达买入订单
            order = client.order_market_buy(
                symbol=f'{type_b}USDT',
                quantity=quantity  # DOGE通常没有小数位
            )
            purchase_cost = usdt_balance
            buy_time = datetime.now()

            send_wechat_message(f"usd余额{usdt_balance},  可买入{round(quantity, 5)}个{type_b}")

            order_id = order['orderId']
            start_time = time.time()
            timeout_seconds = 10

            while True:
                time.sleep(1)  # 每 10 秒检查一次

                # 获取订单状态
                order_status = client.get_order(symbol=f'{type_b}USDT', orderId=order_id)

                # 检查订单状态是否已成交
                if order_status['status'] == 'FILLED':
                    cummulativeQuoteQty = round(float(order.get('cummulativeQuoteQty')), 5)
                    executedQty = round(float(order.get('executedQty')), 5)
                    purchase_cost = cummulativeQuoteQty

                    send_wechat_message(f"Order has been filled. ${cummulativeQuoteQty} 买了{executedQty} 个{type_b}")
                    send_wechat_message(f'{order_status}')
                    break

                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    client.cancel_order(symbol=f'{type_b}USDT', orderId=order_id)
                    send_wechat_message("Order cancelled due to timeout.")
                    break


        else:
            # send_wechat_message(f"Insufficient USDT balance or below minimum trading amount:{usdt_balance}.")
            pass
    except Exception as e:
        send_wechat_message(f"An error occurred while buying {type_b}: {e}")


def sell_doge():
    global las_sell_time
    try:
        global purchase_cost

        if doge_balance and current_doge_value > 1:  # 确保有足够的DOGE且大于最低交易数量
            # 下达卖出订单
            quantity = Decimal(doge_balance).quantize(Decimal('0.001'), rounding=ROUND_DOWN)  # 截断为4位小数

            order = client.order_market_sell(
                symbol=f'{type_b}USDT',
                quantity=quantity  # DOGE通常没有小数位

            )
            las_sell_time = datetime.now()
            send_wechat_message(f"{type_b}余额{doge_balance}g个,  全卖了")

            order_id = order['orderId']
            start_time = time.time()
            timeout_seconds = 10

            while True:
                time.sleep(1)  # 每 10 秒检查一次

                # 获取订单状态
                order_status = client.get_order(symbol=f'{type_b}USDT', orderId=order_id)

                # 检查订单状态是否已成交
                if order_status['status'] == 'FILLED':
                    cummulativeQuoteQty = round(float(order.get('cummulativeQuoteQty')), 5)
                    executedQty = round(float(order.get('executedQty')), 5)

                    beni = cummulativeQuoteQty - purchase_cost

                    send_wechat_message(
                        f"Order has been filled. {executedQty} 个{type_b}卖了 ${cummulativeQuoteQty}, 收益是{beni}")
                    send_wechat_message(f'{order_status}')

                    break

                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    client.cancel_order(symbol=f'{type_b}USDT', orderId=order_id)
                    send_wechat_message("Order cancelled due to timeout.")
                    break


        else:
            # send_wechat_message("Insufficient ETH balance or below minimum trading amount.")
            pass
    except Exception as e:
        send_wechat_message(f"An error occurred while selling {type_b}: {e}")


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
        # 创建消费者线程
        set_btc_thread = threading.Thread(target=set_btc)
        set_btc_thread.start()
        # 创建WebSocket客户端实例
        my_client = SpotWebsocketStreamClient(on_message=message_handler, on_error=on_error, on_close=close_handler)

        # 订阅BTC/USDT的聚合交易流
        my_client.agg_trade(symbol="btcusdt")

        while True:
            time.sleep(10)  # check every ten seconds if the websocket is alive
            if not my_client.socket_manager.is_alive():
                raise Exception("WebSocket connection is not alive")


    except Exception as e:
        send_wechat_message(f"Connection failed: {e}")
        print(f'e')
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

        if not stop_threads:  # 用于控制线程停止的信号

            try:
                print('启动')
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
