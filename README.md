# 配膳ロボット Physical AI 試作

日本語の指示をローカルQwen3で解釈し、MuJoCo上の配膳台車を動かすアプリです。「2番テーブルと3番テーブルの間へ」「1番の近くへ」「部屋の右上へ」などから候補と経路を表示し、利用者が確認してから移動します。

以下は **macOS向けの利用手順**です。空間指定機能はmainに含まれています。コード・評価の詳細は [詳細README](serving_robot/README.md) を参照してください。

## 1. 用意するもの

- GitとPython。検証済みはApple M1・RAM 8 GB・macOS 27.0.1・Python 3.9.6です。Windows/Linuxや別のPythonバージョンでの導入は未検証です。
- 実AIを使う場合は、公式の [Ollama](https://ollama.com/download/mac) を別途導入し、ターミナルで `ollama` コマンドを使用できるようにしてください。[macOSの公式導入説明](https://docs.ollama.com/macos) を参照してください。
- 初回のPython依存・モデル取得にはインターネット接続が必要です。モデル `qwen3:1.7b` は約1.4 GBです。モデル・Ollama本体・仮想環境はこのリポジトリに含まれません。

記録済みの構成はMuJoCo 3.2.7、NumPy 2.0.2、Ollama 0.40.11、Qwen3のQ4_K_M版です。Python依存は固定ファイルから導入します。新しいOllama等への互換性を保証するものではありません。

## 2. コードとPython環境を準備する

例として `~/projects/serving-robot` にcloneします。別の場所を選ぶ場合は、以後の `cd` も同じ場所に読み替えてください。すでにclone済みならcloneを繰り返さず、そのリポジトリへ移動してください。

```sh
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/shiraiwa0425/serving-robot.git
cd serving-robot
python3 -m venv .venv
.venv/bin/python -m pip install -r serving_robot/requirements-lock.txt
```

ここからのコマンドは、特記がなければ **リポジトリのルート**で実行します。仮想環境のactivateは不要です。

## 3. 実AIで起動する

### ターミナル1：Ollamaサーバー

まず、すでに同じMacでOllamaが動いているか確認します。

```sh
curl --silent --fail http://127.0.0.1:11434/api/version
```

バージョンが返る場合は二重起動せず、その既存サーバーを利用するか、管理している人に設定を確認してください。下の環境変数は、新しく起動するサーバーにだけ反映されます。既存アプリやサービスを勝手に停止する必要はありません。

応答がなく、新しくサーバーを起動する場合：

```sh
cd ~/projects/serving-robot
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
export OLLAMA_MODELS="$PWD/models"
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
export OLLAMA_CONTEXT_LENGTH=2048
export OLLAMA_KEEP_ALIVE=2m
ollama serve
```

このターミナルは開いたままにします。この起動例はlocalhost限定で、クラウド機能を無効にします。初回起動時にはOllamaが `~/.ollama/id_ed25519` と `.pub` を生成する場合があります。秘密鍵の内容を表示したり、GitHubへ含めたりしないでください。

### ターミナル2：モデルの準備とアプリ

ターミナルをもう一つ開きます。

```sh
cd ~/projects/serving-robot
export OLLAMA_HOST=127.0.0.1:11434
ollama pull qwen3:1.7b
.venv/bin/python -B serving_robot/app.py --backend ollama --model qwen3:1.7b --port 8767
```

`ollama pull` はモデル取得用です。同じモデルを取得済みなら省略できます。モデルの保存先はOllamaサーバー側の設定によります。通常起動のたびにモデルをダウンロードする必要はありません。

`http://127.0.0.1:8767 backend=ollama` と表示されたら、**同じMacのブラウザ**で次を開きます。

**http://127.0.0.1:8767/**

画面に `LOCAL AI · qwen3:1.7b` と出れば実AIモードです。`localhost` は見ている端末自身を意味するので、別のiPhone/PCから同じURLを開くことはできません。この手順はネットワーク公開を設定しません。

### AIなしで画面・制御だけを試す場合

Python環境を準備済みなら、Ollamaやモデルなしで次も使えます。実AIアプリと同時に使う例として別ポートにしています。

```sh
cd ~/projects/serving-robot
.venv/bin/python -B serving_robot/app.py --backend mock --port 8768
```

ブラウザで http://127.0.0.1:8768/ を開きます。`MOCK · 実AI未使用` と表示されます。これはルールによるテスト用の代替で、AIによる成功や課題のAI使用要件とは区別してください。

## 4. 画面を操作する

1. 入力欄に、例えば **「2番テーブルと3番テーブルの間へ」** と入力して「候補を作る」を押します。推論中は停止します。
2. 黄色い候補と破線の経路、候補の位置・説明を確認します。この時点では移動しません。
3. よければ **「この候補へ移動」** を押します。現在位置から経路を再検査し、緑の経路に沿って移動します。
4. 違う場所なら **「候補を取り消す」** を押すか、新しい指示を送ります。古い候補は使えなくなります。
5. 移動を止めるときは **「停止・候補を取り消す」** を押します。AIの応答を待たず停止処理を行います。減速には短い時間がかかり、瞬間停止ではありません。

指示の例：

| 入力例 | 扱い |
|---|---|
| `1番へ配膳して` / `厨房に戻って` | 登録済み地点の候補 |
| `2番テーブルと3番テーブルの間へ` | 異なる2卓の間の候補 |
| `1番の近くへ` | 指定卓の周辺候補 |
| `部屋の右上へ` / `部屋の左下へ` | 画面基準の角付近の候補 |
| `部屋の右下へ` | 卓を避けて角付近で補正した候補。位置を確認してください |
| `2番と3万の間へ` / `12番の近くへ` / `部屋の角へ` | 推測せず確認要求。移動しません |

すべての移動に確認が必要です。曖昧・矛盾・未対応の指定や、安全で到達可能な候補がない場合は、停止したまま画面に説明します。

## 5. 終了する

- 台車の移動・候補だけを止める：画面の **「停止・候補を取り消す」**。
- アプリのサーバーを終了する：ターミナル2で **Ctrl+C**。
- 自分で起動したOllamaを終了する：ターミナル1で **Ctrl+C**。他のアプリと共有している既存サーバーは管理者に確認してください。

アプリを終了するとWeb画面は操作できなくなります。次回はOllamaの稼働を確認し、アプリ起動コマンドを再実行します。

## 困ったとき・制限・評価

- 画面が開かない場合、アプリのターミナルが開いたままか、指定したポートとURLが同じか確認してください。
- `ollama: command not found`、推論エラー、ポート使用中などは [詳細READMEの対処](serving_robot/README.md) を参照してください。
- 固定の6×6 m地図と既知の自己位置が前提です。カメラSLAM、任意座標、実機、自由な位置関係は未対応です。実機での安全は保証しません。
- 空間機能の開発22例はAI素出力15/22、検査後22/22です。一般的な日本語理解の精度を示すものではありません。過去の比較・失敗・試験記録は [詳細README](serving_robot/README.md) にまとめています。

**このREADME改善案の導入コマンドは、コードCLIとの静的照合のみ行っています。新規clone・依存導入・モデル取得からの一連の動作試験は未実施です。**
