# 建议在根目录创建 main.py 作为入口点
# main.py
from app import app

if __name__ == "__main__":
    app.run(debug=True)