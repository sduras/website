from flask import Flask, request, jsonify
import smtplib
import ssl
import socks
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# NOTE: These variables should be configured with your actual email details
MAIL_USER = "your_email_user"
MAIL_PASSWORD = "your_email_password"
MAIL_HOST = "your_mail_server.onion"
MAIL_PORT = 587
MAIL_RECEIVER = "receiver@example.com"

# In a real application, you would configure Flask properly.
app = Flask(__name__)

@app.route("/send_email", methods=["POST"])
def send_email():
    """
    Handles a POST request to send an email.
    The email is routed through a Tor SOCKS5 proxy and the SSL handshake
    is manually handled to provide the server_hostname.
    """
    name = request.form.get("name")
    email = request.form.get("email")
    message = request.form.get("message")

    if not all([name, email, message]):
        return jsonify({"error": "🔔 All fields are required"}), 400

    msg = MIMEMultipart()
    msg["From"] = f"{MAIL_USER}@{MAIL_HOST}"
    msg["To"] = MAIL_RECEIVER
    msg["Subject"] = "🧅 New message from Tor contact form"

    body = f"""
New message from your Tor site:

Name: {name}
Email: {email}
Message:
{message}
    """
    msg.attach(MIMEText(body, "plain", _charset="utf-8"))

    try:
        # Configuration for the SOCKS5 proxy to Tor
        SOCKS_HOST = "127.0.0.1"
        SOCKS_PORT = 9050

        print(f"🛠 Creating SOCKS5 proxy socket with rdns=True to {MAIL_HOST}:{MAIL_PORT}")
        socks.set_default_proxy(socks.SOCKS5, SOCKS_HOST, SOCKS_PORT, rdns=True)
        tor_socket = socks.socksocket()
        tor_socket.settimeout(30)
        tor_socket.connect((MAIL_HOST, MAIL_PORT))

        print("🌐 Connected to SMTP server over Tor")

        # Initialize SMTP object
        smtp = smtplib.SMTP()
        smtp.set_debuglevel(2)
        smtp.sock = tor_socket  # Use the pre-connected Tor socket

        # Manually call connect (without hostname resolution) and get initial reply
        smtp.file = smtp.sock.makefile("rb")
        code, response = smtp.getreply()
        print(f"🔁 Initial server response: {code} {response}")

        # Send EHLO command
        smtp.ehlo("localhost.localdomain")

        # Issue STARTTLS command and check for a successful reply
        code, resp = smtp.docmd("STARTTLS")
        if code != 220:
            print(f"❌ Server did not accept STARTTLS: {code} {resp}")
            raise smtplib.SMTPException(f"STARTTLS not supported by server: {resp}")

        # Manually wrap the socket with SSL to upgrade the connection
        # This allows us to explicitly pass the server_hostname
        print("🔐 Manually upgrading the socket with SSL...")
        tor_socket = ssl.wrap_socket(tor_socket, server_hostname=MAIL_HOST)
        smtp.sock = tor_socket
        # The file object needs to be recreated for the new socket
        smtp.file = smtp.sock.makefile("rb", 0)

        # Re-EHLO over the now-encrypted connection
        print("🤝 Re-negotiating connection with EHLO over TLS...")
        smtp.ehlo("localhost.localdomain")

        # Log in and send the email
        print("🔑 Logging in...")
        smtp.login(MAIL_USER, MAIL_PASSWORD)
        print("📧 Sending email...")
        smtp.sendmail(msg["From"], MAIL_RECEIVER, msg.as_string())
        print("🚪 Quitting SMTP session...")
        smtp.quit()

        print("✅ Email sent successfully.")
        return jsonify({"success": True}), 200

    except Exception as e:
        print("❌ Exception during email sending:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)




