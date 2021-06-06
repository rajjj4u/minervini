import io

import requests
from nsepy import get_history
from nsetools import Nse
from pandas_datareader import data as pdr
# from yahoo_fin import stock_info as si
from pandas import ExcelWriter
# import yfinance as yf
import pandas as pd
import datetime
import time

from flask import render_template, url_for, flash, redirect
from screener import app


posts = [
    {
        'author': 'Corey Schafer',
        'title': 'Blog Post 1',
        'content': 'First post content',
        'date_posted': 'April 20, 2018'
    },
    {
        'author': 'Jane Doe',
        'title': 'Blog Post 2',
        'content': 'Second post content',
        'date_posted': 'April 21, 2018'
    }
]


@app.route("/home")
def home():
    return render_template('home.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')

@app.route("/")
@app.route("/screen")
def screen():
    exportList = pd.DataFrame(
    columns = ['Stock', "RS_Rating", "50 Day MA", "150 Day Ma", "200 Day MA", "52 Week Low", "52 week High"])
    returns_multiples = []

    # Variables
    url = "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv"  # replace 100 for NIFTY100, 500 etc
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
        'X-Requested-With': 'XMLHttpRequest'
    }
    s = requests.get(url, headers=headers).content
    df = pd.read_csv(io.StringIO(s.decode('utf-8')))
    tickers = list(df['Symbol'])
    tickers.sort()

    index_name = 'NIFTY'  # S&P 500
    start_date = (datetime.datetime.now() - datetime.timedelta(days=365)).date()
    end_date = datetime.date.today()
    exportList = pd.DataFrame(
    columns = ['Stock', "RS_Rating", "Close", "50 Day MA", "150 Day Ma", "200 Day MA", "52 Week Low", "52 week High"])
    returns_multiples = []
    # Index Returns
    index_df = get_history(symbol='NIFTY',
    start = start_date,
    end = end_date,
    index = True
    )
    print(index_df['Close'][0])
    print(index_df['Close'][-1])
    index_df['Percent Change'] = index_df['Close'].pct_change()
    index_return = (index_df['Percent Change'] + 1).cumprod()[-1]
    print(f'index_return={index_return}')

    print(f'TICKERS={tickers}')

    # Find top 30% performing stocks (relative to the S&P 500)
    # for ticker in tickers:
    # # Download historical data as CSV for each stock (makes the process faster)
    #     df = get_history(symbol=ticker,
    #                      start = start_date,
    #                      end = end_date)
    #     df.to_csv(f'data/{ticker}.csv')
    #
    #     # Calculating returns relative to the market (returns multiple)
    #     print(f"Processing {ticker} - oldest={df['Close'][0]} and latest={df['Close'][-1]}")
    #     df['Percent Change'] = df['Close'].pct_change()
    #     stock_return = (df['Percent Change'] + 1).cumprod()[-1]
    #     print(f'stock_return={stock_return}')
    #
    #     returns_multiple = round((stock_return / index_return), 2)
    #     returns_multiples.extend([returns_multiple])
    #
    #     print(f'Ticker: {ticker}; Returns Multiple against {index_name}: {returns_multiple}\n')
    #     time.sleep(1)
    #
    # # # Creating dataframe of only top 30%
    # rs_df = pd.DataFrame(list(zip(tickers, returns_multiples)), columns=['Ticker', 'Returns_multiple'])
    # rs_df['RS_Rating'] = rs_df.Returns_multiple.rank(pct=True) * 100
    # rs_df = rs_df[rs_df.RS_Rating >= rs_df.RS_Rating.quantile(.70)]
    # #
    # rs_df.to_pickle('data/rs_df.pkl')
    rs_df = pd.read_pickle('data/rs_df.pkl')
    # Checking Minervini conditions of top 30% of stocks in given list
    rs_stocks = rs_df['Ticker']
    stocks_above_200_ma = 0
    for stock in rs_stocks:
        try:
            df = pd.read_csv(f'data/{stock}.csv', index_col=0)
            sma = [50, 150, 200]
            for x in sma:
                df["SMA_" + str(x)] = round(df['Close'].rolling(window=x).mean(), 2)

            # Storing required values
            currentClose = df["Close"][-1]
            moving_average_50 = df["SMA_50"][-1]
            moving_average_150 = df["SMA_150"][-1]
            moving_average_200 = df["SMA_200"][-1]
            low_of_52week = round(min(df["Low"][-260:]), 2)
            high_of_52week = round(max(df["High"][-260:]), 2)
            RS_Rating = round(rs_df[rs_df['Ticker'] == stock].RS_Rating.tolist()[0])

            try:
                moving_average_200_20 = df["SMA_200"][-20]
            except Exception:
                moving_average_200_20 = 0

            # Condition 1: Current Price > 150 SMA and > 200 SMA
            condition_1 = currentClose > moving_average_150 > moving_average_200

            # Condition 2: 150 SMA and > 200 SMA
            condition_2 = moving_average_150 > moving_average_200

            # Condition 3: 200 SMA trending up for at least 1 month
            condition_3 = moving_average_200 > moving_average_200_20

            # Condition 4: 50 SMA> 150 SMA and 50 SMA> 200 SMA
            condition_4 = moving_average_50 > moving_average_150 > moving_average_200

            # Condition 5: Current Price > 50 SMA
            condition_5 = currentClose > moving_average_50

            # Condition 6: Current Price is at least 30% above 52 week low
            condition_6 = currentClose >= (1.3 * low_of_52week)

            # Condition 7: Current Price is within 25% of 52 week high
            condition_7 = currentClose >= (.75 * high_of_52week)

            if currentClose > moving_average_200:
                stocks_above_200_ma += 1

                # If all conditions above are true, add stock to exportList
            if (
                    condition_1 and condition_2 and condition_3 and condition_4 and condition_5 and condition_6 and condition_7):
                exportList = exportList.append(
                    {'Stock': stock, "Close": currentClose, "RS_Rating": RS_Rating, "50 Day MA": moving_average_50,
                     "150 Day Ma": moving_average_150, "200 Day MA": moving_average_200,
                     "52 Week Low": low_of_52week, "52 week High": high_of_52week},
                    ignore_index=True)
                print(stock + " made the Minervini requirements")
        except Exception as e:
            print(e)
            print(f"Could not gather data on {stock}")

    print(f'stocks_above_200_ma={stocks_above_200_ma}')
    exportList = exportList.sort_values(by='RS_Rating', ascending=False)
    print('\n', exportList)
    # writer = ExcelWriter("ScreenOutput.xlsx")
    # exportList.to_excel(writer, "Sheet1")
    # writer.save()
    file_name = f'NIFTY {str(datetime.date.today())} TRENDING STOCKS.csv'
    exportList.to_csv(file_name, index=None)
    return render_template('screen.html', exportList=exportList)

    return "<h1>DONE</h1>"
    # document = open(file_name, 'rb')
    # doc = InputFile(document)
    # bot.sendDocument(chat_id=group_id, document=doc, filename=f'{str(datetime.date.today())}_TRENDING_STOCKS.csv', caption=f'Minervini’s Trend Template - {str(datetime.date.today())}')
    # msg = list(exportList["Stock"])


