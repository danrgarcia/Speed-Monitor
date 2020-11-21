import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import speedtest
from datetime import datetime
import psycopg2
from os import getenv
import time
import matplotlib.pyplot as plt

monitor_host = getenv('monitor_host')
monitor_db = getenv('monitor_db')
monitor_user = getenv('monitor_user')
monitor_pass = getenv('monitor_pass')
from_address = getenv('from_address')
from_password = getenv('from_password')
to_address = getenv('to_address')


def connect_to_postgresql():
    conn = psycopg2.connect(
        host=monitor_host,
        user=monitor_user,
        password=monitor_pass)

    return conn


def start_monitoring(speed):
    date_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    down_speed = round((round(speed.download()) / 1048576), 2)
    up_speed = round((round(speed.upload()) / 1048576), 2)
    print(f"time: {date_time}, downspeed: {down_speed} Mb/s, upspeed: {up_speed} Mb/s")

    update_db(date_time, down_speed, up_speed)


def update_db(date_time, down_speed, up_speed):
    conn = connect_to_postgresql()
    cur = conn.cursor()
    cur.execute("INSERT INTO monitoring VALUES(%s, %s, %s)", (date_time, down_speed, up_speed))
    conn.commit()
    print("Data entered into table")
    conn.close()


def create_table():
    conn = connect_to_postgresql()
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS monitoring(time_ran TIMESTAMP, down_speed DECIMAL, up_speed DECIMAL)")
    conn.commit()
    conn.close()


def get_data():
    times = []
    download = []
    upload = []
    conn = connect_to_postgresql()
    cur = conn.cursor()
    cur.execute("SELECT time_ran::time, down_speed, up_speed FROM monitoring WHERE time_ran::date = %s",
                (datetime.now().strftime('%Y-%m-%d'),))
    runs = cur.fetchall()
    conn.close()
    for run in runs:
        times.append(str(run[0]))
        download.append(run[1])
        upload.append(run[2])

    return times, download, upload


def create_graph():
    run_times, download_speed, upload_speed = get_data()
    current_date = datetime.now().strftime('%Y-%m-%d')
    filename = 'Speed_Graph_' + current_date + '.jpg'
    plt.plot(run_times, download_speed, label='download', color='r')
    plt.plot(run_times, upload_speed, label='upload', color='b')
    plt.xlabel('time')
    plt.ylabel('speed in Mb/s')
    plt.legend()
    plt.title(current_date)
    plt.savefig(filename, bbox_inches='tight')

    send_report(filename)


def send_report(filename):
    msg = MIMEMultipart()

    msg['From'] = from_address
    msg['To'] = to_address
    msg['Subject'] = "Daily Internet Speed Stats"
    body = "Attached are your internet speeds for the day."

    msg.attach(MIMEText(body, 'plain'))

    attachment = open(filename, "rb")

    p = MIMEBase('application', 'octet-stream')

    p.set_payload(attachment.read())
    encoders.encode_base64(p)
    p.add_header('Content-Disposition', "attachment; filename= %s" % filename)
    msg.attach(p)

    s = smtplib.SMTP('smtp.gmail.com', 587)

    s.starttls()
    s.login(from_address, from_password)
    text = msg.as_string()
    s.sendmail(from_address, to_address, text)
    s.quit()


if __name__ == '__main__':
    create_table()
    s = speedtest.Speedtest()
    end_of_day = datetime.now().strftime('%Y-%m-%d 17:00:00')
    end_of_day = datetime.strptime(end_of_day, '%Y-%m-%d %H:%M:%S')
    while datetime.now() < end_of_day:
        start_monitoring(s)
        time.sleep(600)
    create_graph()
