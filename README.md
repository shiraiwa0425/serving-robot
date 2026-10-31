# 配膳ロボット Physical AI 試作

日本語の指示をローカルQwen3で解釈し、MuJoCo上の配膳台車を動かすアプリです。「2番テーブルと3番テーブルの間へ」「1番の近くへ」「部屋の右上へ」などから候補と経路を表示し、利用者が確認してから移動します。

以下は **MacとWSL 2（Ubuntu）向けの利用手順**です。空間指定機能はmainに含まれています。コード・評価の詳細は [詳細README](serving_robot/README.md) を参照してください。

## 1. 用意するもの

**この手順は、Ollama・モデル・Python仮想環境がまだないMacまたはWSLで初めてcloneする場合を想定しています。** Ollamaはモデルを動かしてローカルAPIを提供するランタイム／サーバーで、指示を解釈するLLM本体は **Qwen3（`qwen3:1.7b`）** です。開発者の環境やclone外のフォルダには依存しません。

- GitとPython。検証済みはApple M1・RAM 8 GB・macOS 27.0.1・Python 3.9.6です。WSL 2（Ubuntu）や別のPythonバージョンでの導入は未検証です。
- 実AIを使う場合はOllama CLIが必要です。未導入の場合のMac／WSL向けコマンドを下に記載しています。Homebrewを使う例は **Homebrew導入済み** が前提です。
- 初回のPython依存・モデル取得にはインターネット接続が必要です。モデル `qwen3:1.7b` は約1.4 GBです。モデル・Ollama本体・仮想環境はこのリポジトリに含まれません。

記録済みの構成はMuJoCo 3.2.7、NumPy 2.0.2、Ollama 0.40.11、Qwen3のQ4_K_M版です。Python依存は固定ファイルから導入します。新しいOllama等への互換性を保証するものではありません。

## 2. コードとPython環境を準備する

WSLは **WSL 2とUbuntuを導入済み** とし、コマンドはすべてUbuntuターミナル内で実行します。OllamaもPythonアプリも同じWSL内で動かし、Windows側のOllamaには接続しません。WSL自体の導入は対象外です。UbuntuでGit・curl・Python・venvが未導入の場合は、最初に次を実行します（sudo権限とインターネット接続が必要）。

```sh
sudo apt-get update
sudo apt-get install -y git curl python3 python3-venv python3-pip
```

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

### 初回のみ：macOSでOllama CLIを導入する

最初に既存CLIとサーバーを確認します。既存のOllamaがある場合は再インストールせず利用します。

```sh
command -v ollama
curl --show-error --silent --fail --max-time 3 http://127.0.0.1:11434/api/version
```

`command -v` がパスを返すなら導入済みです。APIだけ応答する場合もサーバーは既にあります。別の場所に導入済みのCLIを確認し、重複インストールしないでください。標準のmacOSアプリを導入済みでCLIがPATHにない場合は、次で **このターミナルだけ** CLIを使えます。

```sh
export PATH="/Applications/Ollama.app/Contents/Resources:$PATH"
command -v ollama
```

**CLIもサーバーもなく、新規導入する場合だけ**、以下を実行します。この例はGUIアプリのcaskではなく、`ollama` コマンドを提供するHomebrew **formula** を使います。

```sh
if command -v ollama >/dev/null 2>&1; then
  printf '%s\n' 'Ollama CLIは導入済みです。再インストールしません。'
elif command -v brew >/dev/null 2>&1; then
  brew install ollama
else
  printf '%s\n' 'Homebrewが見つかりません。この手順はHomebrew導入済みが前提です。'
fi
```

Homebrew自体がない場合は、[Homebrew公式導入案内](https://brew.sh/)で前提条件を確認して準備してから戻ってください。上記はHomebrewを自動導入せず、`brew services start` による自動起動も設定しません。[formulaの現行情報](https://formulae.brew.sh/formula/ollama)で対応OS・CPUを確認できます。環境に対応するバイナリがない場合、ソースビルドが必要になることがあります。

導入後にCLIを確認します。見つからない場合は、モデル取得へ進む前にHomebrewのPATH設定を確認してください。

```sh
command -v ollama
ollama --version
```

Ollama公式macOSアプリの現行要件はSonoma 14以降ですが、Homebrew formulaの対応範囲はformulaの現行情報で別途確認してください。

### 初回のみ：WSL 2（Ubuntu）でOllamaを導入する

Ubuntuターミナルで既存CLIとサーバーを確認します。どちらかが存在する場合は導入先を確認し、再インストールしないでください。

```sh
command -v ollama
curl --show-error --silent --fail --max-time 3 http://127.0.0.1:11434/api/version
```

**両方が未導入の場合だけ**、同じUbuntu内で公式Linuxインストーラーを実行します。これはWSL内のLinux用で、Macでは実行しません。

```sh
if curl -fsSL https://ollama.com/install.sh -o /tmp/serving-robot-ollama-install.sh; then
  sh /tmp/serving-robot-ollama-install.sh
fi
command -v ollama
ollama --version
```

これは[公式Linux導入コマンド](https://docs.ollama.com/linux)のスクリプトを保存してから実行する形です。システムへの導入にsudo権限を使い、環境によってサービス作成・起動も行います。実行前にスクリプトを確認してください。GPUやsystemdの状態により挙動が異なるため、導入後は必ず下記API確認を行い、応答するなら `ollama serve` を重ねて実行しません。

以降のモデル取得・起動・確認はMac／WSLで共通です。WSLでは引き続き同じUbuntu内で実行します。ローカルモデルを使うためクラウド用のサインインやAPIキーは不要です。今回のHomebrew導入例・WSL導入・最新Ollamaでの通し試験は未実施です。

### ターミナル1：Ollamaサーバー

まず、すでに同じ環境（Mac、または同じWSL Ubuntu）でOllamaが動いているか確認します。

```sh
curl --show-error --silent --fail --max-time 3 http://127.0.0.1:11434/api/version
```

バージョンが返る場合は二重起動せず、その既存サーバーを利用するか、管理している人に設定を確認してください。下の環境変数は、新しく起動するサーバーにだけ反映されます。既存アプリやサービスを勝手に停止する必要はありません。

Ollamaアプリを開いたことで既に応答する場合もあります。応答があるなら `ollama serve` を追加実行せず、次の「ターミナル2」へ進みます。応答がなければアプリの起動状態・エラーを確認し、サーバーが未起動の場合だけ、次のCLI起動例を使います。タイムアウトや不明な応答の場合は、二重起動を試す前に既存サービスの状態を確認してください。

新しくCLIからサーバーを起動する場合：

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
curl --show-error --silent --fail --max-time 3 http://127.0.0.1:11434/api/version
ollama pull qwen3:1.7b
ollama list
curl --show-error --silent --fail --max-time 3 http://127.0.0.1:11434/api/tags
```

`api/version` でJSONのバージョン応答が返ること、`ollama list` のNAME列と `api/tags` のmodelsに **`qwen3:1.7b`** があることを確認します。接続エラーや取得失敗の場合は、アプリ起動へ進まずOllama側を確認してください。`models: []` はサーバー接続は成功していますがモデル未取得です。

`ollama pull` はOllamaの配布元からモデルを取得します。Hugging Faceから別途ファイルを直接ダウンロードしたり、Python用のOllama SDKを追加導入したりする必要はありません。このアプリはPython標準ライブラリでローカルAPIへ接続します。

`ollama pull` はモデル取得用です。同じモデルを取得済みなら省略できます。モデルの保存先はOllamaサーバー側の設定によります。通常起動のたびにモデルをダウンロードする必要はありません。

モデル名は可変タグであり、将来も同じ配布内容とは限りません。新しい環境の `ollama --version` と `ollama list` のモデルIDを記録し、過去の評価と区別してください。

接続とモデルを確認できたら、同じターミナル2・cloneのルートで実AIアプリを起動します。

```sh
.venv/bin/python -B serving_robot/app.py --backend ollama --model qwen3:1.7b --port 8767
```

接続の流れは **ブラウザ → Pythonアプリ（127.0.0.1:8767）→ Ollama（127.0.0.1:11434）→ Qwen3** です。`OLLAMA_HOST` はOllama CLI／サーバー向けで、アプリ自身の接続先は実装上11434に固定されています。

`http://127.0.0.1:8767 backend=ollama` と表示されたら、**Macのブラウザ、またはWSLを動かしているWindowsのブラウザ**で次を開きます。

**http://127.0.0.1:8767/**

画面に `LOCAL AI · qwen3:1.7b` と出れば実AIモードです。WSLでは通常、WindowsのブラウザからWSL内のWebアプリをlocalhostで開けます（[WSL公式ネットワーク説明](https://learn.microsoft.com/en-us/windows/wsl/networking)）。開けない場合はWSLのlocalhost転送状態を確認してください。OllamaとPythonは同じWSL内なので、相互接続のIP変更や外部公開は不要です。`localhost` は見ている端末自身を意味するので、別のiPhone/PCから同じURLを開くことはできません。この手順はネットワーク公開を設定しません。

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

**このREADMEの導入コマンドは、コードCLIとの静的照合のみ行っています。新規clone・依存導入・モデル取得からの一連の動作試験は未実施です。**
