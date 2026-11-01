# 設定・トラブル対応・実装と評価

初めて使う方は [ルートREADMEのセットアップと操作手順](../README.md) から始めてください。以下のコマンドは、特記がなければcloneのルートで実行します。

## コマンドと実行場所

| CLI | 内容 |
|---|---|
| `--backend mock` | AIなしのルールによるテスト用代替。省略時もmock |
| `--backend ollama` | localhostのOllamaを使う実AIモード |
| `--model qwen3:1.7b` | 実AIで利用する取得済みモデル名 |
| `--port 8767` | Web画面のポート。省略時8767 |

Ollama接続先は実装内で `http://127.0.0.1:11434/api/chat` に固定されています。アプリの `--port` はWeb画面用であり、Ollamaのポートを変更するオプションではありません。仮想環境はモデルを含まず、モデル取得だけでもPython依存は準備されません。

## 起動時の補足

ブラウザ → Pythonアプリ（8767）→ Ollama（11434）→ Qwen3の順で接続します。モデルは `ollama pull` で取得でき、Hugging Faceからの直接取得やPython用Ollama SDKは不要です。モデルの保存先はサーバー設定によります。

公式インストーラーはMacではアプリとCLIリンクを配置して起動し、既存アプリは停止・置換します。WSLではsystemdの状態に応じてユーザー・サービス作成と自動起動を設定します。初回Ollama起動時には `~/.ollama/id_ed25519` と `.pub` を生成する場合があります。鍵・モデル・仮想環境はGitへ含めないでください。

省メモリ用に新しくCLIサーバーを起動する場合の例です。既存サーバーには反映されません。

```sh
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 OLLAMA_CONTEXT_LENGTH=2048 OLLAMA_KEEP_ALIVE=2m ollama serve
```

AIなしで画面・制御だけを試す場合：

```sh
.venv/bin/python -B serving_robot/app.py --backend mock --port 8768
```

http://127.0.0.1:8768/ を開きます。`MOCK · 実AI未使用` はルールによる代替で、実AIの成功とは区別してください。

## よくある問題

| 症状 | 確認すること |
|---|---|
| `ollama: command not found` | [ルートREADME](../README.md#1-初回セットアップ)で既存CLI・サーバーを確認。未導入の場合だけ公式インストールコマンドを実行。導入済みならCLIのPATHを確認し、二重インストールしない |
| `.venv/bin/python` がない | ルートREADMEのvenv作成を行ったか。カレントディレクトリがcloneのルートか |
| `No module named mujoco` | 同じvenvのPythonで `-m pip install -r serving_robot/requirements-lock.txt` を行ったか |
| 依存のインストールに失敗 | 検証済みPythonは3.9.6。別のPython/OSでの互換性は未検証。既存の他環境を上書きせず、エラーとバージョンを確認 |
| ブラウザで接続できない | サーバーが稼働中か。アプリ起動時のポートとURLが同じか。MacまたはWSLホストWindowsから開いているか |
| `Address already in use` | 同じポートの既存サーバーを二重起動していないか。アプリは例として `--port 8769` に変更し、ブラウザも `http://127.0.0.1:8769/` に合わせる。無関係なサービスを停止しない |
| `api/tags` の `models` が空／モデルがない | 接続中のサーバーに `OLLAMA_HOST=127.0.0.1:11434 ollama pull qwen3:1.7b` で取得し、同じ接続先の `ollama list` を再確認。保存先はサーバー設定による |
| 推論に失敗・確認待ち | Ollamaが11434で応答するか、モデル名と取得状況が正しいか。別ターミナルで `OLLAMA_HOST=127.0.0.1:11434 ollama list` を確認。初回ロードの遅延もある |
| 候補が出ても動かない | 正常な確認待ちか確認。「この候補へ移動」で開始。減速中は確認が一時的に無効になる |
| 古い候補が無効と表示 | 新指示・停止・取り消し・既に確認済みで候補が失効した。最新の指示で新しい候補を作る |
| 四隅や「近く」が想像と違う | 指定範囲内で障害物を避けるため補正される。候補位置を確認し、違う場合は取り消す |

サーバー状態の読み取り確認：

```sh
curl --show-error --silent --fail --max-time 3 http://127.0.0.1:11434/api/version
curl --show-error --silent --fail --max-time 3 http://127.0.0.1:11434/api/tags
curl --silent --fail http://127.0.0.1:8767/state
```

`api/tags` のmodelsが空なら未取得です。モデル名を確認してからアプリを使ってください。WSLの画面が開かない場合は [localhost転送](https://learn.microsoft.com/en-us/windows/wsl/networking) を確認します。OllamaとPythonを同じUbuntu内で動かすため、両者の接続に外部公開は不要です。

導入手順はCLI・接続先・画面ラベルとの静的照合のみです。新規環境・WSLでの通し実行は未検証です。

## 以前の開発配置について

通常のcloneでは親フォルダのvenvや起動スクリプトは使いません。同梱の `run-ollama.sh` はclone内の `.tools/ollama/ollama` と `models` を準備済みの場合の補助で、インストーラーではありません。標準手順では不要です。旧ポート8766も必須ではなく、現在の既定は8767です。

## 検証済み構成とモデル

- Apple M1・RAM 8 GB、macOS 27.0.1、Python 3.9.6。
- MuJoCo 3.2.7、NumPy 2.0.2。Python依存は [requirements-lock.txt](requirements-lock.txt) に固定。
- Ollama 0.40.11、`qwen3:1.7b`、Q4_K_M。モデル関連レイヤー合計1,359,294,303 bytes。
- 記録したモデルdigest：`8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`。
- タグは1.7bですが、配布側メタデータは2.0Bと報告。タグや配布物の将来の変更を固定するものではありません。[整合性の検証記録](artifacts/model-integrity.json) を参照。
- モデルはApache-2.0、Ollama本体はMIT。モデル・環境・鍵をGitへ含めない構成です。
- 空間解釈の設定はthink=false、temperature=0、context2048、生成上限180 tokens、HTTP timeout45秒。旧4地点解釈は128 tokens。
- 記録上のOllamaモデル割当は約1.21 GB。OSやプロセス全体の総RAM・ピーク使用量ではありません。他の機器での余裕や速度は未検証です。

## 地図・物理・対応範囲

入力例は「1番へ配膳して」「厨房に戻って」「2番テーブルと3番テーブルの間へ」「1番の近くへ」「部屋の右上へ」です。「2番と3万の間へ」「12番の近くへ」「部屋の角へ」は推測せず確認要求に戻します。右下などは障害物を避けて補正するため、候補を確認してください。新指示・取り消し・停止で古い候補は失効します。


6×6 mの固定地図、厨房、3卓、中央障害物を用います。台車は半径0.22 m・質量約8 kg、平面拘束された全方向移動モデルです。MuJoCoが速度サーボ、力上限、接触と時間発展を計算し、ブラウザのSVGがその状態を表示します。単なるUIアニメーションではありませんが、車輪・荷物・人・実センサーの詳細モデルではありません。

AIは `landmark / between / near / corner` とランドマークを構造化します。別の検査が番号全体・関係・否定・候補数を照合し、一致する場合だけ地図側で座標を作ります。

- `between`：異なるテーブル2卓の中心の中点から最大0.3 mの範囲。
- `near`：テーブル1卓の辺・角から0.4〜0.5 m離した有限候補。厨房の近くは未対応。
- `corner`：画面基準の四隅。壁から0.5 m離れた基準点の半径1 m以内。右下は卓を避けて約0.8 m補正する例がある。
- 登録済み地点：厨房・1番卓・2番卓・3番卓。

0.1 mグリッドのA*、障害物から台車中心まで半径+0.10 m、壁から中心まで0.32 mの余白を検査し、実位置とグリッドの接続線も確認します。確認時は現在位置から再計画。候補がなければ別地点へ無制限に丸めず、停止して説明します。

新指示は推論前に経路と古い候補を失効させます。候補IDと世代番号で連打・古い確認・遅い推論結果を拒否。停止ボタンと対応する停止表現はAI待ちより優先します。減速には時間がかかり、瞬間停止ではありません。

固定された正確な地図と自己位置が前提です。任意座標、自由な位置関係、カメラSLAM、実機は対象外。未知表現への精度や、実機での安全を保証しません。

## 保存された評価結果

以下は過去の実行記録で、今回のREADME修正時に再測定した値ではありません。

| 評価段階 | 件数 | AI素出力 | 検査後 |
|---|---:|---:|---:|
| 旧方式・初回開発 | 20 | 14/20 | 14/20 |
| 旧方式・同じ20例を改善後 | 20 | 20/20 | 20/20 |
| 旧方式・事前固定した追加表現 | 15 | 11/15 | 15/15 |
| 空間指定・初回開発 | 22 | 15/22 | 21/22 |
| 空間指定・構造不正を確認へ戻す修正後 | 同じ22 | 15/22 | 22/22 |

旧20例の単純キーワード方式は9/20、AI未使用mockは11/20です。旧初回の誤移動6例、追加15例の誤提案4例、空間指定初回の構造不正1例を含め、結果を上書きせず [artifacts](artifacts) に保存しています。

空間指定の修正後は中央値0.603秒・最大0.982秒、初回最大4.096秒はモデルロード込みです。同じ開発問題で改善しており、未知表現への一般化性能ではありません。追加15例にも仕様に近い手作業の言い換えが含まれます。AI単独で空間指定22/22を達成したわけではありません。

最終差分の26テスト（回帰7・空間/物理/確認15・HTTP4）とUI状態テスト、実AI統合6ケースの保存記録があります。[最終テスト](artifacts/spatial-release-tests.txt)、[UI状態テスト](artifacts/spatial-release-ui.txt)、[実AI統合](artifacts/spatial-live-v1.json) を参照。

テストを自分で実行する場合は、clone内のvenvを準備し、次のブロックだけ `serving_robot` ディレクトリで実行します。

```sh
cd ~/projects/serving-robot/serving_robot
../.venv/bin/python -B -m unittest -v test_robot test_spatial test_spatial_http
```

HTTP試験は一時localhostサーバーを起動して終了時に閉じます。`test_robot` は `artifacts/routes.json` を再出力するため、結果変更が作業ツリーへ現れる場合があります。既存Webアプリの停止は不要です。UI状態テストはNode.jsが導入済みの場合に `node test_spatial_ui.mjs` で実行できます。Nodeはアプリ起動の必須依存ではありません。

`test_live.py` は確認導入前の履歴用です。新方式の `test_spatial_live.py` は8767のアプリを実際に操作するため、利用中のセッションでは実行しないでください。保存結果の自動上書きもしません。

## 公式資料

- [Ollama macOS導入](https://docs.ollama.com/macos)
- [Ollamaの環境変数・運用説明](https://docs.ollama.com/faq)
- [Qwen3のOllama配布](https://ollama.com/library/qwen3:1.7b)
- [開発元モデルカード](https://huggingface.co/Qwen/Qwen3-1.7B)
