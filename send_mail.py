"""Optional: email the day's new signals via Gmail SMTP (needs GMAIL_USER + GMAIL_APP_PASSWORD repo secrets)."""
import json, os, smtplib, ssl
from email.message import EmailMessage
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data")
L=json.load(open(os.path.join(D,"latest.json")))
if not L["new_signals"]: print("no new signals — no mail"); raise SystemExit
rows="".join(f"<tr><td>{s['rule']}</td><td><b>{s['symbol']}</b></td><td>{s['industry']}</td><td>₹{s['signal_close']}</td><td>{s['mcap']}</td><td>{s['pe']}</td><td>{s['pgrowth']}%</td><td>{s['lo250']}×</td></tr>" for s in L["new_signals"])
html=f"""<p>New buy signal(s) from the NSE Small-Cap Rally Finder for data through <b>{L['last_data_date']}</b>. Buy at tomorrow's open, −10% stop on the intraday low, hold 40 trading days, take every signal.</p>
<table border="1" cellpadding="6" style="border-collapse:collapse;font-family:Arial;font-size:13px"><tr><th>Rule</th><th>Stock</th><th>Industry</th><th>Signal close</th><th>Mcap ₹cr</th><th>P/E</th><th>Profit growth</th><th>× off 52-wk low</th></tr>{rows}</table>
<p>Dashboard: https://jj-jimmy88.github.io/nse-rally-finder/</p>"""
m=EmailMessage(); m["Subject"]=f"[Rally Finder] {len(L['new_signals'])} new buy signal(s) — {', '.join(s['symbol'] for s in L['new_signals'])}"
m["From"]=os.environ["SMTP_USER"]; m["To"]=os.environ.get("MAIL_TO","jj.jimmy88@gmail.com"); m.set_content("New signals: "+", ".join(s['symbol'] for s in L["new_signals"])); m.add_alternative(html,subtype="html")
with smtplib.SMTP_SSL("smtp.gmail.com",465,context=ssl.create_default_context()) as s:
    s.login(os.environ["SMTP_USER"],os.environ["SMTP_PASS"]); s.send_message(m)
print("mail sent")
