import time

# Prevent spam alerts
last_alert_time = 0

def send_sms_alert(to_number, message):
    global last_alert_time

    current_time = time.time()

    # Send only once every 60 seconds
    if current_time - last_alert_time < 60:
        return "⚠️ Alert recently sent (avoiding spam)"

    last_alert_time = current_time

    # Simulated SMS (clean)
    log = f"""
    📱 SMS ALERT SENT
    ----------------------
    To: {to_number}
    Message: {message}
    Time: {time.strftime('%H:%M:%S')}
    """

    print(log)

    return "📱 Alert sent successfully (simulated)"