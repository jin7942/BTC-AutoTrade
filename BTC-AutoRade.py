from urllib import request
import requests
import time
import pyupbit
import datetime
import schedule
from fbprophet import Prophet

access = "YualtmxPiPbjgUP37xsIax6zxqx3Jz1sWyRQ24xo" # 업비트 엑세스 키
secret = "xNWM1sEf0mb7JrAxcGNyWBvjM3SjzvSeX8Z3MALw" # 업비트 시크릿 키
myToken = "xoxb-2996066780438-3015403502001-JpUIxTMYl1THqm8U1bypykK5" # 슬랙 봇 토큰

    # 슬랙 메시지 전송
def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )
    print(response)
    
    # 변동성 돌파 전략으로 매수 목표가 조회
def get_target_price(ticker, k):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

    # 시작 시간 조회
def get_start_time(ticker):
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
    start_time = df.index[0]
    return start_time

    #잔고 조회
def get_balance(ticker):
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

    # 현재가 조회
def get_current_price(ticker):
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]

predicted_close_price = 0
    # Prophet으로 당일 종가 가격 예측
def predict_price(ticker):
    global predicted_close_price
    df = pyupbit.get_ohlcv(ticker, interval="minute60")
    df = df.reset_index()
    df['ds'] = df['index']
    df['y'] = df['close']
    data = df[['ds','y']]
    model = Prophet()
    model.fit(data)
    future = model.make_future_dataframe(periods=24, freq='H')
    forecast = model.predict(future)
    closeDf = forecast[forecast['ds'] == forecast.iloc[-1]['ds'].replace(hour=9)]
    if len(closeDf) == 0:
        closeDf = forecast[forecast['ds'] == data.iloc[-1]['ds'].replace(hour=9)]
    closeValue = closeDf['yhat'].values[0]
    predicted_close_price = closeValue
predict_price("KRW-BTC")
schedule.every().hour.do(lambda: predict_price("KRW-BTC"))

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")
# 시작 메세지 슬랙 전송
post_message(myToken, "#btc-autotrade", "autotrade start")

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()
        start_time = get_start_time("KRW-BTC")
        end_time = start_time + datetime.timedelta(days=1)
        schedule.run_pending()

        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price("KRW-BTC", 0.5)
            current_price = get_current_price("KRW-BTC")
            if target_price < current_price and current_price < predicted_close_price:
                krw = get_balance("KRW")
                if krw > 5000:
                    buy_result = upbit.buy_market_order("KRW-BTC", krw*0.9995)
                    # BTC 구매 슬랙 메시지 전송
                    post_message(myToken, "#btc-autotrade", "BTC buy : " +str(buy_result))
        else:
            btc = get_balance("BTC")
            if btc > 0.00008:
                sell_result = upbit.sell_market_order("KRW-BTC", btc*0.9995)
                # BTC 판매 슬랙 메시지 전송
                post_message(myToken,"#btc-autotrade", "BTC buy : " +str(sell_result))
        time.sleep(1)
    except Exception as e:
        print(e)
        post_message(myToken,"#btc-autotrade", e)
        time.sleep(1)