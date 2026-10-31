# 追加15例：事前固定・一回評価

既存20例、プロンプト、安全制御を変更せず、別セットの期待値を推論前に固定。初回一度だけ評価し、その後の修正・再試験は実施していません。

- AI素出力：11/15。
- 既存安全検査後：15/15。
- 検査介入：4件。すべて確認要求へ戻った。
- 危険な最終誤移動：0件。推論エラー0件。
- 中央値0.307秒、最大3.639秒（初回モデルロードを含む）。
- 明確な移動4例、否定2例、複数目的地2例、曖昧2例、範囲外2例、停止優先3例。
- 停止優先3例はすべてAI素出力もstopだった。

期待値：novel-cases-fixed.json。manifest SHA-256：28116df17d2d0382d8258c4bf0ac4611338225bb5b791ddbd125049dc05795f1。
プロンプトSHA-256：8a6386e3a4f7ca186222a77ea99d8d7f4ccaed2f0f56a29b0f9b248761cf41a8（従来v2と同一）。
intent.pyと既存evaluate.pyの評価前後hashが一致したことも確認。

AI素出力の誤り（隠さず全件）：

- 一番卓に寄って、それから三番卓へ届けて → AI {'action': 'move', 'goal': 'table1'} → 最終 {'action': 'clarify', 'goal': None}（destination_not_unique_or_absent）

- 左側のテーブルに届けて → AI {'action': 'move', 'goal': 'table1'} → 最終 {'action': 'clarify', 'goal': None}（destination_not_unique_or_absent）

- 四番卓へ配膳して → AI {'action': 'move', 'goal': 'table3'} → 最終 {'action': 'clarify', 'goal': None}（destination_not_unique_or_absent）

- テーブル12番へ向かって → AI {'action': 'move', 'goal': 'table1'} → 最終 {'action': 'clarify', 'goal': None}（model_destination_has_no_text_evidence）

## 解釈の限界

未使用の文を評価前に作り、期待値を事前に固定した簡易確認です。ただし作者が同じ課題の仕様を知って手作業で選んだ15例であり、プロンプト中の例や開発20例と語彙・構造が近い言い換えも含みます。モデルの学習データからの独立性や、実利用の分布を代表することは証明できません。モデルの追加学習は行っていません。15/15は制御込みのこのセットに限った結果で、AIが一般に正しいことを示しません。AI素出力11/15と既存検査による4件の補正を必ず併記します。

## 稼働と開始・停止

確認時、http://127.0.0.1:11434/api/version が0.40.11を返し、http://127.0.0.1:8766/state はbackend=ollama、model=qwen3:1.7b、status=clarify、target=null、実速度はほぼ0を返しました。応答は確認済みで、再起動は不要でした。

開始：作業ルートでターミナル1は ./run-ollama.sh、ターミナル2は .venv/bin/python -B serving_robot/app.py --backend ollama --model qwen3:1.7b --port 8766。Macのブラウザーで http://127.0.0.1:8766。

停止：ロボットの移動だけなら画面の「停止」ボタン。UI終了はそのPythonを起動したターミナルでCtrl+C、Ollama終了はrun-ollama.shのターミナルでCtrl+C。各スクリプトはフォアグラウンド実行で、自動起動サービスではありません。UIのCtrl+C終了・再起動は前工程で実行確認済みです。Ollamaの停止操作自体は今回行わず、現在の利用可能状態を維持しました。
