import time
import boto3

import json, requests, urllib, io

from pandas.io.json import json_normalize

import numpy as np
import pandas as pd
import os
import gzip
import sys
from datetime import date


def get_active_meters(API_TOKEN):
    url = "https://utilityapi.com/api/v2/meters"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    r = requests.get(url, headers=headers)
    download = json.loads(r.text)

    active_meters = []

    for i in range(len(download["meters"])):
        if (
            download["meters"][i]["is_activated"] == True
            and download["meters"][i]["is_archived"] == False
        ):
            active_meters.append(download["meters"][i]["uid"])
    return active_meters


def get_bills(API_TOKEN, meter_uid):
    url = f"https://utilityapi.com/api/v2/files/meters_bills_csv?meters={meter_uid}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    download = requests.get(url, headers=headers).content
    return pd.read_csv(io.StringIO(download.decode("utf-8")), error_bad_lines=False)


def test_demand_kw_in_bills(API_TOKEN):
    no_demand_kw = []
    all_active = get_active_meters(API_TOKEN)
    for i in all_active:
        try:
            get_bills(API_TOKEN, i)["Demand_kw"]
            return_code = 0
        except Exception as e:
            return_code = 1
        if return_code == 1:
            no_demand_kw.append(i)
    return no_demand_kw


# send bills dataframe to S3


def send_bills_to_s3_with_demand_kw(API_TOKEN, meter_uid, AWS_PROFILE, BUCKET_NAME):

    cols = [
        "meter_uid",
        "utility",
        "utility_service_id",
        "utility_billing_account",
        "utility_service_address",
        "utility_meter_number",
        "utility_tariff_name",
        "bill_start_date",
        "bill_end_date",
        "bill_days",
        "bill_statement_date",
        "bill_total_kWh",
        "bill_total",
        "bill_volume",
        "bill_total_unit",
        "Demand_kw",
    ]

    df = get_bills(API_TOKEN, meter_uid)[cols]

    print(f"Loading {len(df)} Rows to S3 for meter_uid {meter_uid}")

    load_date = date.today().strftime("%Y-%m-%d")
    print("Load Date:", load_date)

    session = boto3.session.Session(
        profile_name=AWS_PROFILE,
    )
    s3_client = session.client("s3", use_ssl=False)

    csv_buffer = io.StringIO()

    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    gz_buffer = io.BytesIO()

    with gzip.GzipFile(mode="w", fileobj=gz_buffer) as gz_file:
        gz_file.write(bytes(csv_buffer.getvalue(), "utf-8"))
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"""bills/{load_date}/meter_uid_{meter_uid}_bills.csv.gz""",
            Body=gz_buffer.getvalue(),
        )
        return_code = 0
    except Exception as e:
        return_code = 1
        print(e)
    return return_code


def send_bills_to_s3_without_demand_kw(API_TOKEN, meter_uid, AWS_PROFILE, BUCKET_NAME):

    cols = [
        "meter_uid",
        "utility",
        "utility_service_id",
        "utility_billing_account",
        "utility_service_address",
        "utility_meter_number",
        "utility_tariff_name",
        "bill_start_date",
        "bill_end_date",
        "bill_days",
        "bill_statement_date",
        "bill_total_kWh",
        "bill_total",
        "bill_volume",
        "bill_total_unit",  #'Demand_kw'
    ]

    df = get_bills(API_TOKEN, meter_uid)[cols]

    print(f"Loading {len(df)} Rows to S3 for meter_uid {meter_uid}")

    load_date = date.today().strftime("%Y-%m-%d")
    print("Load Date:", load_date)

    session = boto3.session.Session(
        profile_name=AWS_PROFILE,
    )
    s3_client = session.client("s3", use_ssl=False)

    csv_buffer = io.StringIO()

    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    gz_buffer = io.BytesIO()

    with gzip.GzipFile(mode="w", fileobj=gz_buffer) as gz_file:
        gz_file.write(bytes(csv_buffer.getvalue(), "utf-8"))
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"""bills/{load_date}/meter_uid_{meter_uid}_bills.csv.gz""",
            Body=gz_buffer.getvalue(),
        )
        return_code = 0
    except Exception as e:
        return_code = 1
        print(e)
    return return_code


def get_intervals(API_TOKEN, meter_uid):
    url = f"https://utilityapi.com/api/v2/files/intervals_csv?meters={meter_uid}"
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }
    download = requests.get(url, headers=headers).content
    return pd.read_csv(io.StringIO(download.decode("utf-8")), error_bad_lines=False)


# Send intervals dataframe to s3


def send_intervals_to_s3(API_TOKEN, meter_uid, AWS_PROFILE, BUCKET_NAME):
    df = get_intervals(API_TOKEN, meter_uid)
    df.astype = {
        "meter_uid": int,
        "utility": str,
        "utility_service_id": int,
        "utility_service_address": str,
        "utility_meter_number": int,
        "utility_tariff_name": str,
        "interval_start": str,
        "interval_end": str,
        "interval_kWh": int,
        "net_kWh": int,
        "source": str,
        "updated": str,
        "interval_timezone": str,
    }

    print(f"Loading {len(df)} Rows to S3 for meter_uid {meter_uid}")

    load_date = date.today().strftime("%Y-%m-%d")
    print("Load Date:", load_date)

    session = boto3.session.Session(
        profile_name=AWS_PROFILE,
    )
    s3_client = session.client("s3", use_ssl=False)

    csv_buffer = io.StringIO()

    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    gz_buffer = io.BytesIO()

    with gzip.GzipFile(mode="w", fileobj=gz_buffer) as gz_file:
        gz_file.write(bytes(csv_buffer.getvalue(), "utf-8"))
    try:
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=f"""intervals/{load_date}/meter_uid_{meter_uid}_intervals.csv.gz""",
            Body=gz_buffer.getvalue(),
        )
        return_code = 0
    except Exception as e:
        return_code = 1
        print(e)
    return return_code
