# 配膳ロボットの小さな Physical AI 試作

日本語の指示をこのMacのQwen3で解釈し、MuJoCoで計算する台車を厨房・3卓の間で動かす試作です。AIは移動先・停止・確認要求の意図だけを返し、A*経路計画と安全制御が移動を担当します。外部APIは使用しません。

## 実AIで起動

このリポジトリには仮想環境・Ollama本体・モデルを同梱しません。先に下記の固定バージョンを配置してください。`run-ollama.sh` はモデルを取得せず、既存構成を起動します。

ターミナル1：

```sh
cd /path/to/project
./run-ollama.sh
```

ターミナル2：

```sh
cd /path/to/project
.venv/bin/python -B serving_robot/app.py --backend ollama --model qwen3:1.7b --port 8766
```

Macのブラウザーで http://127.0.0.1:8766 を開きます。iPhoneからlocalhostは開けません。画面の例は同梱のスクリーンショットを参照してください。

例：`二番のテーブルまでお願い` → 2番卓への走行。`動くのをやめて` → 停止。`1番か2番へ運んで` → 確認待ち・停止。確認後は行先を一つにして再入力します。

各ターミナルでCtrl+Cを押すと該当プロセスが終了します。自動起動・外部公開は設定していません。Ollamaは127.0.0.1:11434のみ、クラウド機能無効、並列数1、最大ロードモデル数1。未使用2分でモデルが解放されます。起動時の鍵表示を避けるためサーバーログは出しません。鍵内容をコマンドで表示しないでください。

モックも別に利用できます（AI未使用）：

```sh
.venv/bin/python -B serving_robot/app.py --port 8765
```

## 検証した固定構成

- Apple M1・RAM 8 GB、macOS 27.0.1、Python 3.9.6。
- `.venv`：MuJoCo 3.2.7、NumPy 2.0.2。全Python依存は `requirements-lock.txt`。
- `.tools/ollama`：公式Ollama **v0.40.11**、macOS CLI。PATH変更・Applicationsへの移動なし。
- `models`：公式Ollamaタグ **qwen3:1.7b**、Q4_K_M。取得量1,359,294,303 bytes（関連レイヤー込み）。
- 使用モデルの識別digest：`8f68893c685c3ddff2aa3fffce2aa60a30bb2da65ca488b61fff134a4d1730e7`。
- タグは1.7bですが、配布側の実行メタデータはparameter_size=2.0Bと報告しています。容量とdigestを固定し、別モデルへの自動更新はしません。
- モデルApache-2.0、Ollama本体MIT。配布URL・整合性は `artifacts/model-integrity.json` と下記。

Ollama公式CLI archiveのSHA-256：`aea7d3f2e32371b7644a6e2ec8d4f26820a0e3965918cce8a46cef3e947f6291`。公式公開値と一致。コード署名は通常環境で `valid on disk` / `satisfies its Designated Requirement`。sandbox内の証明書検証では不正と表示されたため、設定変更なしの通常環境による検証で切り分けました。署名の変更・無効化はしていません。

モデルはOllama自身のSHA-256検証に加え、全blobのSHA-256とサイズを独立に照合済みです。公式ソフトとモデルの取得は承認済み。別途明示承認を得た `~/.ollama/id_ed25519` と `.pub` が通常権限0600/0644で初回生成されています。鍵内容は表示・レポート転記していません。クラウドログイン・鍵登録・遠隔接続設定は実施していません。

別環境でPythonだけ再現する場合：

```sh
python3 -m venv .venv
.venv/bin/pip install --no-cache-dir -r serving_robot/requirements-lock.txt
```

モデルを再取得する必要がある場合は、公式配布の容量・digest・ライセンスと保存先を先に確認してください。通常起動ではモデル取得しません。

## 設計と物理範囲

- 6×6 m固定地図、厨房、3卓、中央障害物。台車半径0.22 m、質量約8 kg。
- MuJoCoの平面拘束全方向台車。質量、速度サーボ、力上限、接触を計算します。ブラウザーSVGはMuJoCo状態の表示層です。単なるUIアニメーションではありません。
- 車輪・荷物・人・実センサーを詳細再現したものではありません。固定地図、完全な位置情報を前提にしています。
- 0.1 mグリッドのA*、障害物を0.32 m膨張。目標速度上限0.35 m/s。
- 実速度と制動距離を含む安全領域を監視し、危険時は指令ゼロへ切替。サーボで減速するため停止は瞬間ではありません。実機安全保証ではありません。
- AIは厳格なJSONの `move(goal)` / `stop` / `clarify` だけを出力し、座標やモーターを直接制御しません。
- AIのmove提案に対し、明示目的地が一つで提案と一致するか、否定・条件・曖昧表現がないかを別の検査で確認します。この検査は移動先を作らず、疑わしければclarifyに戻すだけです。
- 新しい指示は推論前に経路を解除。確認要求・エラー・不正出力では停止。古い推論結果はepochで無効化し、新しい停止を取り消せません。停止ボタンはAIを経由しません。
- AI設定：think=false、temperature=0、context=2048、生成上限128 tokens、HTTP timeout=45秒。

ネイティブMuJoCoの3Dビューアー（GUI起動は未検証）：

```sh
.venv/bin/mjpython -B serving_robot/viewer.py --goal table2
```

## 固定20例の評価

|方式・段階|正解|曖昧／否定4例で確認|誤った移動|遅延中央値 / 最大|
|---|---:|---:|---:|---|
|単純キーワード|9/20|2/4|2件|計測対象外|
|従来モック（AI未使用）|11/20|4/4|0件|計測対象外|
|実AI v1 初回|14/20|1/4|6件|0.397 / 4.277秒|
|実AI v2 改善後|20/20|4/4|0件|0.321 / 0.964秒|

v1は1番卓を厨房と取り違えた3例と、曖昧な3例で誤移動を返しました。この初回の失敗は `evaluation-ollama-ai-v1.json` に全件保存しています。

v2では対応表と少数の分類例を明確にし、安全検査を追加しました。AI素出力も20/20で、今回の20例における安全検査の介入は0件でした。補正後の数字だけをAIの性能と呼んでいません。

**同じ20例を見て改善した開発用の結果です。未見の表現に対する20/20を示すものではありません。** v1最大値にはモデル初回ロードを含み、v2はロード済み状態で開始したため、最大遅延の単純比較はできません。両評価とも推論エラー0。各指示の全結果と遅延、v2のAI素出力、安全検査理由はJSONに保存。

20例の固定SHA-256：`7f89db4bbba7573e9c616e7cd2d88e8c898160905e8dd79b8a545a231f034406`。ケースは変更していません。段階ごとのintentソースとプロンプトhashも保存。新しい評価名を指定し、過去結果は上書きしません。

```sh
cd /path/to/project/serving_robot
../.venv/bin/python -B -m unittest -v test_robot
../.venv/bin/python -B evaluate.py --backend ollama --model qwen3:1.7b --run my-new-run
```

## 物理・統合・画面検証

- `artifacts/tests-final.txt`：7テスト成功。全16組の経路計画、3卓への物理走行、速度・クリアランス・接触なし、停止、安全領域停止、不正意図、安全検査。制御を外した時に実接触して障害物を通り抜けないことも確認。
- `artifacts/routes.json`：厨房→1卓16.60秒、2卓24.12秒、3卓22.68秒（シミュレーション時間）、接触0、最終誤差約0.028 m、最大実速度約0.306 m/s。
- `artifacts/live-ai-integration.json`：実AIの言い換え移動、言葉による停止、曖昧指示で停止確認、推論中の新しい停止優先、4件すべて成功。
- Chromeでも `二番のテーブルまでお願い` → moving（解釈0.49秒、実速度0.305 m/s）、`動くのをやめて` → stopped・速度0（0.53秒）、`1番か2番へ運んで` → clarify・速度0（0.56秒）を確認。
- `artifacts/robot-local-ai-running.jpg`：実際のChromeの走行画面。従来mock画像と別ファイル。

実AIの統合試験を再実行する場合、既存の `live-ai-integration.json` を別名に保管してから、AIサーバーとUI起動中に `../.venv/bin/python -B test_live.py`。結果を隠さないため既存記録は自動上書きしません。

## 資源と残作業

Ollama `/api/ps` が報告したモデル割当は約1.21 GB（VRAMも同値）、context2048、GPUを使用するllamacpp runner。これはプロセス全体やOSを含む総RAM使用量ではありません。macOSのmemory_pressure -Qでは推論前38%、後24%の空き指標。サンプリング値で、ピークRAMやスワップ量は未測定です。取得後ディスク空きは約20 GiB。1モデルずつ運用してください。

残作業は未見の言い換え・否定・命令注入などの別セットでの評価と、課題の独自性・発表の整理です。公開GitHub、PDF、1〜3分動画、OmniCampus提出はまだ行っていません。親から共有された期限は2026年11月2日AM10:00（タイムゾーン記載なし）。

公式出典：

- https://ollama.com/library/qwen3:1.7b
- https://huggingface.co/Qwen/Qwen3-1.7B
- https://github.com/ollama/ollama/releases/expanded_assets/v0.40.11
- https://docs.ollama.com/macos
- https://docs.ollama.com/api/chat


## 追加の未使用表現15例（一度だけの確認）

期待値を先に固定し、既存20例・プロンプト・制御を変更せず一回だけ評価しました。AI素出力11/15、既存安全検査後15/15。複数・曖昧・範囲外の4件を検査が確認へ戻し、最終誤移動0件。遅延中央値0.307秒、最大3.639秒（ロード込み）。停止優先3例はAI素出力も正解。評価後の修正・再試験なし。

このセットも仕様を知って手作業で作った近い言い換えを含む15例で、一般化性能や学習データからの独立性は証明できません。詳細と全失敗例は `artifacts/novel-evaluation-summary.md`、事前固定期待値は `novel-cases-fixed.json`、全結果は `evaluation-novel-v1.json`。
