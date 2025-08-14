```bash
pkg install python -y
pip install flask -y
pkg install tor -y
git clone https://github.com/sduras/website.git
cd website
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python mirror.py
