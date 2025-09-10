import requests, time, json, logging, schedule
from datetime import datetime

# API 키 입력 (Settings → Secrets → 각각 등록 후 ${…} 형태로 불러오기)
FMP_API_KEY = "${{ secrets.FMP_API_KEY }}"
ALPHA_VANTAGE_KEY = "${{ secrets.ALPHA_VANTAGE_KEY }}"
PERPLEXITY_API_KEY = "${{ secrets.PERPLEXITY_API_KEY }}"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_tickers():
    data = requests.get(f"https://financialmodelingprep.com/api/v3/stock/list?apikey={FMP_API_KEY}").json()
    items = data.get("symbolsList") or data
    return [i["symbol"] for i in items if i.get("symbol")]

def get_prices(tickers):
    out=[]
    for s in tickers[:100]:
        j=requests.get("https://www.alphavantage.co/query", params={'function':'GLOBAL_QUOTE','symbol':s,'apikey':ALPHA_VANTAGE_KEY}).json().get("Global Quote",{})
        try:
            p=float(j["05. price"]); c=float(j["10. change percent"].rstrip("%"))
            out.append({'symbol':s,'price':p,'change':c})
        except: pass
        time.sleep(12)
    return out

def job():
    tickers=get_tickers()
    prices=get_prices(tickers)
    avg=sum(p['change'] for p in prices)/len(prices) if prices else 0
    top_up=sorted(prices, key=lambda x:x['change'], reverse=True)[:5]
    top_dn=sorted(prices, key=lambda x:x['change'])[:5]
    prompt=f"""
분석 시각: {datetime.now():%Y-%m-%d %H:%M}
평균 변동률: {avg:+.2f}%

급등 TOP5:
""" + "\n".join(f"- {u['symbol']} {u['change']:+.2f}%" for u in top_up) + """

급락 TOP5:
""" + "\n".join(f"- {d['symbol']} {d['change']:+.2f}%" for d in top_dn) + """

추천 종목 5개와 이유를 제시해주세요."""
    print(prompt)
    r=requests.post("https://api.perplexity.ai/chat/completions",
        headers={'Authorization':f'Bearer {PERPLEXITY_API_KEY}','Content-Type':'application/json'},
        json={'model':'sonar','messages':[{'role':'user','content':prompt}],'max_tokens':2000,'temperature':0.3}
    )
    print("\n🤖", r.json()['choices'][0]['message']['content'])

schedule.every().day.at("07:00").do(job)

if __name__=="__main__":
    print("스케줄러 시작… 매일 07:00 자동 실행")
    while True:
        schedule.run_pending()
        time.sleep(30)
