# 配膳ロボット Physical AI 試作

日本語の指示で、MuJoCo上の配膳台車を動かすアプリです。ローカルLLM **Qwen3** が行き先を解釈し、**候補と経路を確認してから移動**します。OllamaはQwen3を動かすサーバーです。

## 1. 初回セットアップ

Mac、または導入済みの **WSL 2＋Ubuntu** を使います。Git・Python・curlとインターネット接続が必要です。モデルは約1.4 GB。

### WSL 2＋Ubuntuのみ：必要なツールを準備

**Macでは実行不要です。次の「Mac・WSL共通」へ進んでください。**

WSLでは、以下を含めすべてUbuntuターミナルで実行し、Ollamaとアプリを同じUbuntu内で動かします。必要なツールがなければ先に準備します。

```sh
# WSL 2＋Ubuntu専用。Macでは実行しません。
sudo apt-get update
sudo apt-get install -y git curl zstd python3 python3-venv python3-pip
```

### Mac・WSL共通：cloneとPython環境を準備

コードとPython環境を準備します。clone済みなら、そのフォルダへ移動してください。

```sh
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/shiraiwa0425/serving-robot.git
cd serving-robot
python3 -m venv .venv
.venv/bin/python -m pip install -r serving_robot/requirements-lock.txt
```

Ollamaが未導入の場合だけ、[公式コマンド](https://ollama.com/download/mac)で導入します。既存CLI（`command -v ollama`）やサーバーがあれば再インストールは不要です。インストーラーは権限確認やサービス起動を行う場合があります。

```sh
curl -fsSL https://ollama.com/install.sh | sh
```

## 2. Ollamaを起動する（ターミナル1）

まず応答を確認します。

```sh
curl --show-error --silent --fail --max-time 3 http://127.0.0.1:11434/api/version
```

**バージョンが返れば起動済みです。二重起動せず次へ進みます。** 未起動の場合だけ、次を実行してターミナルを開いたままにします。不明なエラーは[対処方法](serving_robot/README.md#よくある問題)を確認してください。

```sh
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

## 3. モデルを取得してアプリを起動する（ターミナル2）

別ターミナルを開き、**cloneしたフォルダ**で実行します。別の場所へcloneした場合は `cd` を読み替えてください。

```sh
cd ~/projects/serving-robot
export OLLAMA_HOST=127.0.0.1:11434
ollama pull qwen3:1.7b
ollama list
```

一覧に `qwen3:1.7b` があれば、アプリを起動します。取得済みなら次回から `pull` は不要です。

```sh
.venv/bin/python -B serving_robot/app.py --backend ollama --model qwen3:1.7b --port 8767
```

ブラウザで **http://127.0.0.1:8767/** を開きます。Macでは同じMac、WSLではホストWindowsのブラウザを使います。画面の `LOCAL AI · qwen3:1.7b` が実AIモードの目印です。別のiPhoneやPCからはこのURLを開けません。

## 4. 操作する・終了する

1. 「2番テーブルと3番テーブルの間へ」などを入力して **「候補を作る」**。
2. 黄色い候補と経路を確認し、**「この候補へ移動」**。確認前は移動しません。
3. 変更するなら **「候補を取り消す」**、止めるなら **「停止・候補を取り消す」**。

「1番の近くへ」「部屋の右上へ」「厨房に戻って」も試せます。角は画面基準です。曖昧・未対応の指示は確認要求へ戻します。停止はAI待ちより優先しますが、減速に短い時間がかかります。

終了はターミナル2で **Ctrl+C**。自分でターミナル1から起動したOllamaも **Ctrl+C** で終了できます。共有中の既存サーバーは停止しないでください。次回は手順2・3の起動だけで使えます。

## 補足

- [トラブル対応・設定・AIなしの起動](serving_robot/README.md)
- [物理モデル・対応範囲](serving_robot/README.md#地図物理対応範囲)／[評価結果](serving_robot/README.md#保存された評価結果)
- 固定地図の試作です。任意座標・カメラSLAM・実機は未対応で、実機の安全は保証しません。
- 検証済みはM1・RAM 8 GB・Python 3.9.6。今回の導入手順は静的確認のみで、新規環境・WSLでの通し実行は未検証です。
