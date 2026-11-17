# v2.3.0 M1 実測記録 — #5544

対象: Redmine project 318 / #5544、親 #5542、`230_ロードマップ` Wiki version 1。
実測日: 2026-11-17 JST。記録作成: ChatGPT Work（ID 10）。
本書は pipeline 166 の設計調査結果を固定する。最終レビュー・main への反映・Redmine の完了更新は、この作成時点では未実施。
製品機能の採用、対応環境の保証、Phase 4/6 の検証、公開の成功を示す文書ではない。

## 1. 結果と判断範囲

承認された E01–E04 の候補条件と revision/hash のゲートが成立し、hold と 6 compute job が成功した。
424 件の読み取りについて、終了コードの索引と結合ログを照合し、アップロードされた非空 stdout/stderr とバイト単位で一致した。
想定した拒否や不在を観測するコマンドの非 0 は、ジョブの失敗とは区別する。

- E01/E02: 基底環境への既存 install 経路と、追加 OS 準備なしでの venv 作成・導入が成功した。
- E03: `python` がなく既存 install は 127。`python3 -m pip` は標識のない基底環境へ導入できた。
- E04: `python` がなく既存 install は 127。別途実行した基底環境の pip は `externally-managed-environment` で 1。保護の回避は実施していない。
- E03/E04: 最初の venv 作成は ensurepip 不在で 1。`bin/python` と `pyvenv.cfg` は残るが pip は使えない。利用側が `python3-venv` を追加した後、別 venv への yamllint 1.38.0 導入は成功した。
- 全候補: 検査対象の内側に venv を作ると yamllint 同梱の YAML 2 件が列挙対象に加わった。外側配置、実験用 ignore、対象の限定ではこの混入を避けられた。
- E01 の別 job 持ち込み: 移動先の Python 自体は起動したが、yamllint の console script は元の絶対 shebang を保持し、持ち込み先と再コピー先の双方で 127。任意の venv の可搬性を保証しない。

D02/D04/D06・H3 の最終判断は後続の判断工程で行う。今回の必要観測は承認範囲内でそろっており、下記の限界を明示した上で最終レビューへ提示する。

## 2. 入力版・承認・実行順序

| 項目 | 固定値 |
| --- | --- |
| リポジトリ | circleci-orbs-mamono210/yamllint |
| 技術基準 commit | `2fc343180c9e13660889ac5643b75fbcabd513ea` |
| 当初承認計画 commit | `dedbccb25625f9b2baecfd78b688f674d9532277` |
| 当初承認記録 commit | `9bfdc4431792cd9870fc02c02194e1158c6c39ed` |
| 実行に適用した現行計画 commit（main） | `b49d6dfdbd14feb98cfc19e52ed99a912f0f739b` |
| 現行計画ファイル | `.circleci/MEASUREMENT_PLAN_V2_3_0.md` |
| 現行計画 SHA-256 | `1b8b2109460a459bde86268764f455defdf97616a10219a64df6b3fe546df578` |
| 実験 branch | `exp/230-m1` |
| 実験 commit | `611af5c706c263c4b211b26412e587b39adf0d4a` |
| 実験 commit の親 | `dedbccb25625f9b2baecfd78b688f674d9532277` |
| 旧実験 commit（履歴のみ） | `699a626fa37388df295d9bdbae7c610c15bded88` |
| 設定 SHA-256 | `4d0dd1c6fa28d2b575fcc1acab30c20e6386738326da2acfa043f52cb6db487f` |
| commit subject | `Recover temporary measurement configuration for #5544. Do not merge.` |
| pipeline | 166 / `adabfcd0-a333-4da5-94ff-2b4e137cd95a` |
| workflow | `measure-m1` / `186a3f9d-c869-4696-a4a6-47afca0a21a7` |
| workflow 結果 | success |
| pipeline parameters | approved-commit = 上記実験 commit、approved-config-sha256 = 上記設定 hash |

計画版と実験 commit は別の対象であり、互いの SHA 一致を要求しない。
実験 commit は承認元 `dedbccb` の上に測定 config だけを載せる。適用する担当変更・復旧承認は main `b49d6df` の計画書と #5544 の承認記録で特定する。
6 job 全ての `revision-sha`、`config-hash`、`worktree-clean`、`revision-branch`、`commit-subject`、`pipeline` が一致した。
ゲートは `CIRCLE_SHA1`、`CIRCLE_BRANCH` との一致も確認し、成功の note を残した。

承認者は人間のプロジェクト所有者（Redmine ID 3）。日時は全て JST（UTC+09:00）にそろえた。

| 出来事 | JST | 根拠・精度 |
| --- | --- | --- |
| 当初の実測範囲承認 | 2026-11-15 21:41 | 計画 §11.1。受領時計 21:41:47。会話の正確な投稿時刻ではない |
| M1 担当変更承認 | 2026-11-15 22:35 | 計画 §11.1 / #5544。受領時計 22:35:14 |
| 復旧後の新 SHA 承認 | 2026-11-17 21:21 | 計画 §11.1 / #5544。受領時計 21:21:31 |
| 現行計画 main 反映確認の journal | 2026-11-17 22:03:57 | #5544 journal 11293。これより前に main 実体と計画 hash を照合済み |
| workflow 作成 | 2026-11-17 22:06:49.195 | workflow API created_at。これは workflow の時刻 |
| hold 開始 | 2026-11-17 22:06:49.446 | workflow jobs API started_at |
| hold 成功終了 | 2026-11-17 22:09:48.778 | 同 stopped_at。UI は mamono210 / Approved。独立した approved_at フィールドではない |
| 最初の compute job 開始 | 2026-11-17 22:09:50.966 | E01 started_at |
| 全 job 終了 | 2026-11-17 22:12:02.972 | E03 / workflow stopped_at |
| 観測 artifact 402 件の回収完了 | 2026-11-17T22:26:36.495+09:00 | DOWNLOAD_MANIFEST.json。追加の shebang 証拠 3 件も同日に回収 |

復旧承認・計画反映確認 → workflow 作成 → 人間の hold 承認 → 各 compute job 開始、の順を確認した。
ChatGPT が承認済みパラメータで workflow を起動し、人間が hold を承認した。
UI/API の起動アカウント表示は mamono210 であり、担当分担における操作実施者とは分けて扱う。
push による pipeline 165 はパラメータ未指定で No workflows / Not Run だった。今回の実測は 166 の 1 回のみで、再実行していない。

## 3. 実行一覧

| job | 番号 | 結果 | 開始 JST | 終了 JST |
| --- | --- | --- | --- | --- |
| hold-until-approved | 2391 | success | 2026-11-17T22:06:49.446+09:00 | 2026-11-17T22:09:48.778+09:00 |
| m1-E01-carry-in-producer | [2394](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/166/workflows/186a3f9d-c869-4696-a4a6-47afca0a21a7/jobs/2394) | success | 2026-11-17T22:09:51.952+09:00 | 2026-11-17T22:10:22.211+09:00 |
| m1-E01-cimg-py314 | [2396](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/166/workflows/186a3f9d-c869-4696-a4a6-47afca0a21a7/jobs/2396) | success | 2026-11-17T22:09:50.966+09:00 | 2026-11-17T22:11:16.033+09:00 |
| m1-E02-cimg-py313 | [2397](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/166/workflows/186a3f9d-c869-4696-a4a6-47afca0a21a7/jobs/2397) | success | 2026-11-17T22:09:50.985+09:00 | 2026-11-17T22:11:13.198+09:00 |
| m1-E03-ubuntu-2204 | [2392](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/166/workflows/186a3f9d-c869-4696-a4a6-47afca0a21a7/jobs/2392) | success | 2026-11-17T22:09:51.918+09:00 | 2026-11-17T22:12:02.972+09:00 |
| m1-E04-ubuntu-2404 | [2393](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/166/workflows/186a3f9d-c869-4696-a4a6-47afca0a21a7/jobs/2393) | success | 2026-11-17T22:09:51.908+09:00 | 2026-11-17T22:11:51.333+09:00 |
| m1-E01-carry-in-consumer | [2395](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/166/workflows/186a3f9d-c869-4696-a4a6-47afca0a21a7/jobs/2395) | success | 2026-11-17T22:10:25.086+09:00 | 2026-11-17T22:10:39.714+09:00 |

[CircleCI workflow](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/166/workflows/186a3f9d-c869-4696-a4a6-47afca0a21a7?useNewPipelines=false)。設定は Docker executor / small、compute 6 件と executor を使わない approval 1 件。観測 workflow の実際の job 一覧もこの 7 件と一致する。クレジット実消費は取得していない。

## 4. 候補の実体（M-00、M1-01）

下表はタグ名からの推定ではなく、job 内の観測値。E03/E04 の「準備後」は stage A の後、stage B の前。

| 候補 | イメージ参照 | OS | UID | architecture | Python | python3 解決先 | python | 使用 stdlib 標識 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | cimg/python:3.14 | ubuntu 24.04 | 1001 | x86_64 | Python 3.14.10 | /home/circleci/.pyenv/shims/python3 | 有 | 無 |
| E02 | cimg/python:3.13 | ubuntu 22.04 | 1001 | x86_64 | Python 3.13.18 | /home/circleci/.pyenv/shims/python3 | 有 | 無 |
| E03 | ubuntu:22.04 | ubuntu 22.04 | 0 | x86_64 | Python 3.10.12 | /usr/bin/python3 | 無 | 無 |
| E04 | ubuntu:24.04 | ubuntu 24.04 | 0 | x86_64 | Python 3.12.3 | /usr/bin/python3 | 無 | 有 |

E01 の carry-in producer/consumer も E01 と同じ OS・UID 1001・x86_64・Python 3.14.10・基底 stdlib/標識状態を観測した。
E03/E04 の生イメージは UID 0 で、Python/python3/pip/pip3/git/ssh/yamllint を解決できなかった。これらに stage A の利用側準備を施した条件が候補 E03/E04 である。

E01/E02 の `python` と `python3` は pyenv shim。使用中 Python の stdlib はそれぞれ
`/home/circleci/.pyenv/versions/3.14.10/lib/python3.14` と
`/home/circleci/.pyenv/versions/3.13.18/lib/python3.13` で、そこには標識がない。
E01 の `/usr/lib/python3.12/EXTERNALLY-MANAGED` は存在したが、使用中 pyenv Python の標識とは区別する。
E03 の使用 stdlib `/usr/lib/python3.10` には標識がなく、E04 の `/usr/lib/python3.12` には標識がある。
全候補の準備済み基底環境は `sys.prefix == sys.base_prefix`。

Spin up environment ログは取得したが、完全なイメージ digest は出力されておらず取得できなかった。
可変タグと今回の実体を対応付ける記録であり、今後同タグから同じバイト列が得られることまでは保証しない。

## 5. 導入・標識・利用側準備（M1-02、M1-03）

各セルは実際の exit code。NR は条件不成立で実施不要だった読み取りで、成功とは数えない。

| 操作 | E01 | E02 | E03 | E04 |
| --- | --- | --- | --- | --- |
| install.sh 版未指定 | 0 | 0 | 127 | 127 |
| install.sh 1.38.0 指定 | 0 | 0 | 127 | 127 |
| 基底 python3 -m pip install | 0 | 0 | 0 | 1 |
| venv 作成 1 回目 | 0 | 0 | 1 | 1 |
| 1 回目の venv 内 pip | 0 | 0 | 1 | 1 |
| venv --without-pip | 0 | 0 | 0 | 0 |
| 基底 ensurepip import | 0 | 0 | 1 | 1 |
| stage B apt install | NR | NR | 0 | 0 |
| venv 作成 2 回目 | NR | NR | 0 | 0 |
| 2 回目の venv 内 pip | NR | NR | 0 | 0 |
| venv 内 yamllint 導入 | 0 | 0 | 0 | 0 |
| venv 内 yamllint --version | 0 | 0 | 0 | 0 |

E03/E04 の既存 install は `python: command not found`。E04 の基底 pip は別の操作で `externally-managed-environment` を返した。
E03 の基底 pip は `/usr/local/bin/yamllint` を導入した。E01/E02 の基底導入先は使用中 pyenv Python 配下。
これらを venv への導入結果と混同しない。

既存 install の版未指定 → 版指定 → 基底 pip の順に同じ job 内で実行している。
E01/E02 の後二者は既に満たされた依存を確認する成功であり、独立した未導入環境での新規導入 3 回の証拠ではない。
今回、版未指定で解決した yamllint も 1.38.0。今後の最新値を固定する主張ではない。

stage A は `apt-get update` と `apt-get install -y --no-install-recommends python3 python3-pip git ca-certificates openssh-client`。
E03/E04 の UID 0 で実行し、先に `python3-venv` / minor ごとの venv パッケージが not-installed であることを確認した。
stage B は最初の作成 exit=1、pip exit=1 を受けて `apt-get install -y --no-install-recommends python3-venv` を実行した。
この apt 準備は利用側の権限・作業であり、Orb の提供機能ではない。root 不要の apt 導入可否は実測していない。

| 候補 | stage A 記録パッケージ版 | stage B 追加版 | 導入後 venv pip |
| --- | --- | --- | --- |
| E03 | git 1:2.34.1-1ubuntu1.18; python3 3.10.6-1~22.04.1; python3-pip 22.0.2+dfsg-1ubuntu0.7 | python3-venv 3.10.6-1~22.04.1 | pip 22.0.2 from /tmp/meas/venv/lib/python3.10/site-packages/pip (python 3.10) |
| E04 | git 1:2.43.0-1ubuntu7.4; python3 3.12.3-0ubuntu2.1; python3-pip 24.0+dfsg-1ubuntu1.3 | python3-venv 3.12.3-0ubuntu2.1 | pip 24.0 from /tmp/meas/venv/lib/python3.12/site-packages/pip (python 3.12) |

E01/E02 は UID 1001 で追加 apt なしに venv 作成・導入が成立し、stage B を実施しなかった。venv pip は 26.2.2。
E03/E04 の最初の失敗には実体の残存があり、削除せず `/tmp/meas/venv-partial` へ退避した。
`--without-pip` は全候補で 0 であり、venv 作成と pip の bootstrap は別の条件として観測できた。

全候補の完成 venv は `/tmp/meas/venv`、`sys.executable` は `/tmp/meas/venv/bin/python`。
`sys.base_prefix` は E01/E02 が各 pyenv Python、E03/E04 が `/usr`。
全候補で yamllint 1.38.0、依存は pathspec 1.1.1 / PyYAML 6.0.3 を導入した。
E04 の venv 内から stdlib を引いた場合も `/usr/lib/python3.12/EXTERNALLY-MANAGED` は残っていた。
標識の削除・sudo・保護回避オプションなしで、基底への拒否と別 venv への成功が両立した。

## 6. 生成ファイルと対象選択（M1-04）

内側・外側で独立した同内容の fixture を使用した。各 fixture は `.yamllint`、`tree/ok.yml`、`tree/ok.yaml`、非 YAML の `tree/notes.txt`。
`.yamllint` は実験 checkout からコピーしたもの。列挙を行う yamllint は、両配置とも M1-03 の `/tmp/meas/venv/bin/yamllint` 1.38.0。
列挙結果は fixture 外の `/tmp/meas/listings` に保存し、ソートした前後を同一候補内で比較した。

| 候補 | 内側 前→後 | 追加相対パス（共通 prefix は ./venv-in-tree/lib/） | 外側 前→後 | 実験 ignore | targets=tree | lint . exit |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | 3 → 5 | python3.14/site-packages/yamllint/conf/default.yaml および relaxed.yaml | 3 → 3 | 3 件 | 2 件 | 0 |
| E02 | 3 → 5 | python3.13/site-packages/yamllint/conf/default.yaml および relaxed.yaml | 3 → 3 | 3 件 | 2 件 | 0 |
| E03 | 3 → 5 | python3.10/site-packages/yamllint/conf/default.yaml および relaxed.yaml | 3 → 3 | 3 件 | 2 件 | 0 |
| E04 | 3 → 5 | python3.12/site-packages/yamllint/conf/default.yaml および relaxed.yaml | 3 → 3 | 3 件 | 2 件 | 0 |

内側の diff は全候補 1（差分あり）、外側の diff は全候補 0（差分なし）。非 YAML の notes.txt は列挙されない。
ignore は CLI に `-d "{extends: relaxed, ignore: [venv-in-tree/]}"` を渡した実験限定の条件であり、製品 `.yamllint` を変更していない。
これは repository 設定へ ignore だけを追記した比較ではなく、そのインライン設定を明示指定した結果である。
`--list-files tree` では既存の `.yamllint` 自体も対象から外れ、2 件となった。
追加 YAML が今回 lint エラーにならなかったことと、意図しない列挙対象の増加は別の観測。

## 7. 配置・再実行・持ち込み（M1-05）

| ケース | E01 | E02 | E03 | E04 |
| --- | --- | --- | --- | --- |
| 非空ディレクトリ | 0 | 0 | 0 | 0 |
| 通常ファイル | 1 | 1 | 1 | 1 |
| 模擬残存物 partial/bin | 0 | 0 | 0 | 0 |
| 実際の失敗残存物 | NR | NR | 0 | 0 |
| 実残存物への作成後 pip | NR | NR | 0 | 0 |
| 完成済み venv へ再作成 | 0 | 0 | 0 | 0 |
| 再作成後 yamllint version | 0 | 0 | 0 | 0 |
| 同じ先へ連続 2 回作成 | 0 | 0 | 0 | 0 |
| 相対パス | 0 | 0 | 0 | 0 |
| 引用された ~ | 0 | 0 | 0 | 0 |
| 引用された $ 変数 | 0 | 0 | 0 | 0 |
| シェル展開後の変数 | 0 | 0 | 0 | 0 |

通常ファイルへの作成は `Unable to create directory '/tmp/meas/place/regular-file'` で拒否された。
非空ディレクトリへの作成成功は、未知の既存ファイルをすべて保全できる保証ではない。keep ファイルの内容・全属性を独立比較する読み取りはない。
完成済み venv へ通常の `python3 -m venv` を再実行した後も、yamllint 1.38.0 は使えた。`--clear` や強制削除の挙動は測定していない。

実際の失敗残存物は E03/E04 でのみ生じ、stage B 後の同パスへの作成と pip が成功した。
E01/E02 の「実際の残存物」ケースは該当物がなく未実行。模擬残存物のケースとは区別する。

全候補で相対先は `/tmp/meas/place/relative`。
引用された `~/meas-tilde` は `/tmp/meas/place/~/meas-tilde`、引用された `$MEAS_PLACE/meas-var` は `/tmp/meas/place/$MEAS_PLACE/meas-var` に生成された。
シェルが展開した `${MEAS_PLACE}/expanded-var` は `/tmp/meas/place/expanded-var` となった。
この結果は実験コマンドのクォート条件に対応し、将来の Orb パラメータが展開する仕様を採用したものではない。

### E01 の別 job 持ち込み

producer は `/tmp/meas/carry/venv` を作り、yamllint 1.38.0 の導入・起動が 0。
CircleCI workspace を consumer の `/tmp/meas/carried` へ attach した。

| 読み取り | exit | 観測 |
| --- | --- | --- |
| producer-version | 0 | yamllint 1.38.0 |
| carried-version | 127 | /tmp/meas/carried/venv/bin/yamllint: cannot execute: required file not found |
| carried-prefix | 0 | /tmp/meas/carried/venv /tmp/meas/carried/venv/bin/python |
| carried-relocated | 127 | cp -a で /tmp/meas/relocated へコピー後も yamllint は required file not found |

追加回収した producer・carried・relocated の console script は、いずれも先頭行が
`#!/tmp/meas/carry/venv/bin/python` だった。`pyvenv.cfg` の command も元の作成先を保持していた。
移動先 Python の prefix 確認は成功した一方、console script は旧絶対 interpreter パスを参照するため起動できない、という証拠の対応である。

同一絶対パスへ復元するケース、consumer での `python -m yamllint`、別 OS/architecture/Python 版への移送は未実行。
E02–E04 の持ち込みも未実行であり、E01 に限定する承認済み Phase 1 の限界を維持する。

### 後始末の範囲

実験ファイルは `/tmp/meas` と job checkout 内。部分失敗の残存物を退避して再作成する観測を行い、製品の自動削除・再利用動作は実装していない。
コンテナ外の利用者ファイルの削除はなく、実行後のホスト側コンテナ消去そのものは独立には検査していない。
CircleCI workspace/artifact は保存された証拠であり、即時削除済みとはしない。
承認計画 §8/9 の恒久的な後始末は証拠退避・main 反映後の実験 branch 削除で、現在は未実施。

## 8. 導入先と実行対象（M1-06）

全候補の venv console script は `/tmp/meas/venv/bin/yamllint`、shebang は `#!/tmp/meas/venv/bin/python`。
モジュールの位置・版、`python -m yamllint --version` も照合した。

| 候補 | command -v yamllint（venv 導入後） | module __file__ / version | module 起動 exit |
| --- | --- | --- | --- |
| E01 | /home/circleci/.pyenv/shims/yamllint | /tmp/meas/venv/lib/python3.14/site-packages/yamllint/__init__.py 1.38.0 | 0 |
| E02 | /home/circleci/.pyenv/shims/yamllint | /tmp/meas/venv/lib/python3.13/site-packages/yamllint/__init__.py 1.38.0 | 0 |
| E03 | /usr/local/bin/yamllint | /tmp/meas/venv/lib/python3.10/site-packages/yamllint/__init__.py 1.38.0 | 0 |
| E04 | ABSENT | /tmp/meas/venv/lib/python3.12/site-packages/yamllint/__init__.py 1.38.0 | 0 |

`/tmp/meas/venv/bin` を PATH に追加する処理はなく、既定の名前解決は完成 venv を指さなかった。
E01/E02/E03 は先行する基底導入先を解決し、E04 は ABSENT。E04 の `path-resolution` exit=0 は不在時に `echo ABSENT` する観測用コマンドの終了値であり、yamllint が見つかったことを表さない。
`pip show -f` の Location は各 `/tmp/meas/venv/lib/pythonX.Y/site-packages` だった。表示・lint・保存処理でどの interpreter を使うかの比較は #5545 の対象。

## 9. D02・D04・D06 と #5545 への引き継ぎ

| 論点 | 判断材料 | この実測で確定しないこと |
| --- | --- | --- |
| D02: 導入方式 | python 名不在と PEP 668 拒否を独立観測。E04 でも準備済み venv への導入は成功 | 新 install の仕様、保護回避、既定挙動の変更 |
| D04: 配置・再利用 | 通常ファイルは拒否、通常の再作成は成功。クォートでパス解釈が変わり、異なる絶対パスへの持ち込みでは console script が起動不可 | 既存パスを削除/再利用する製品仕様、すべての既存ファイルの保全、任意 venv の可搬性 |
| D06: 必須候補範囲 | E01–E04 は M-00 の役割に一致。E03 は標識なし python3 のみ、E04 は標識あり python3 のみ | この準備を製品の対応条件として最終採用すること、可変タグの将来の実体 |
| H3: 利用側準備 | Ubuntu では stage A と、失敗後の stage B を分けて測定 | OS パッケージ導入を Orb の責任にすること |
| #5545: 環境・配置 | 各候補の実測 Python/pip/marker、venv の絶対パスと PATH 不一致、console script/shebang を引き継ぐ | M1 の実体が M2 に残ること。M2 は新 job で再同定・再導入する |

M2 は承認済み `exp/230-m2` / `ebd63fd1426dab201f5190b7e337e65eed09ca5a`、設定 SHA-256
`4ac54e23315313794f32f0052bf5f0e00eac092231c4cbbfb604d66bfbce2375` を前提とする。
#5544 の完了と本書の成果物版の確定が先であり、この記録の作成だけで M2 を開始しない。
M1 で成功した準備は M2 の入力条件を説明するが、同一コンテナ・同一導入物の引き継ぎを意味しない。
M2 では M-00 の再確認により可変タグ・パッケージの変化を検出する。

## 10. 未実行・観測限界

| 対象 | 状態・理由 | 判断への制限 |
| --- | --- | --- |
| E05 Debian 12 | 未実行。E04 が候補条件を満たしたため予備候補は使用しない | Debian 12 の実測結果は本書にない |
| E01/E02 stage A/B | 実施不要。基底条件と最初の venv/pip が成立 | apt 準備が実行済みとはしない |
| E01/E02 実失敗残存物 | 未実行。M1-03 が失敗せず該当物なし | 模擬 partial の結果で代替した成功扱いをしない |
| E03/E04 準備前 stdlib marker | 未取得。python3 がなく stdlib パスを算出できない | /usr/lib の検索結果と、準備後の使用 stdlib 標識を区別 |
| E02–E04 carry-in | 承認上 E01 のみ | 別環境への一般化は不可 |
| carry-in 同一パス復元・module 起動 | 設定にケースがなく未実行 | 全ての持ち込み方法が失敗するとはしない |
| 既存ファイル全保全・強制削除 | 未実行。削除仕様の採用は対象外 | venv exit=0 だけで安全な再利用を保証しない |
| イメージ digest | 取得した spin-up ログに完全 digest なし | タグ・観測実体は特定できるがバイト同一性は固定できない |
| リモート branch 削除 | 未実施。main への証拠反映後 | クリーンアップ済みとはしない |
| 成果物 main 反映・Redmine 完了 | レビュー前のため未実施 | #5544 の完了や #5545 開始を先取りしない |

## 11. 実行範囲と main の照合（M1-07）

6 compute job と hold のみ。測定設定には setup、pack/publish、`CIRCLECI_ORBS` context の参照がない。
測定後の E01–E04 の `main-not-touched` は実験 checkout の `git status --porcelain && git diff --stat` が空という観測であり、リモート main の検証をこれだけで代用しない。
別途 GitHub の main HEAD を再取得し、ローカル取得済みの exact commit で次を照合した。

```text
main = b49d6dfdbd14feb98cfc19e52ed99a912f0f739b
baseline = 2fc343180c9e13660889ac5643b75fbcabd513ea

git diff --name-status baseline main
A	.circleci/MEASUREMENT_PLAN_V2_3_0.md

git diff --name-status experiment^ experiment
M	.circleci/config.yml
```

| ファイルの版 | SHA-256 |
| --- | --- |
| baseline .circleci/config.yml | bbaca8dce8cae7118dcc720aa49475ca8cb3bf9f507b6f7d23f0ad4aad80941a |
| main .circleci/config.yml | bbaca8dce8cae7118dcc720aa49475ca8cb3bf9f507b6f7d23f0ad4aad80941a |
| exp/230-m1 .circleci/config.yml | 4d0dd1c6fa28d2b575fcc1acab30c20e6386738326da2acfa043f52cb6db487f |

main config と baseline config はバイト単位で同一。`git log --oneline main -- .circleci/config.yml` に相当する履歴の最新は以下。

```text
9bdc52b627986e18a6da4ba02c8a621387f554e1 Phase 5 回帰と互換性の検証を公開条件に組み込んだ refs #5492
```

したがって、今回確認した main には測定設定は混入していない。本納品 patch は本書 1 ファイルの新規追加だけを含む。
実験 branch や実験 `.circleci/config.yml` を main にマージしない。

## 12. 証拠保存と完了条件のレビュー

判定に必要な観測値・診断・コマンド・終了コードを本書に内包し、後日の CircleCI 保存期限だけに依存しない。
生データは `yamllint-5544-m1-results.zip` の `evidence/`、解析値は `observations.json`、照合結果は `validation.json`。
計画が採用した保存根拠は Free / artifact 30 日既定値・pipeline 90 日で、個別組織の数値を UI で直接読めなかった限界を維持する。今回の必要証拠は実測当日に回収した。

回収対象は結合ログ、索引、全アップロード済み raw readings、全 listing、測定 helper。402 件に加え spin-up 6 件と carry-in の console script 3 件を保存した。
生成された venv ディレクトリ全体（依存 wheel や Python 実体等）は再配布しない。artifact 全件の path/URL 索引は metadata に保持する。
空 stdout/stderr は artifact 一覧に含まれない場合があるが、結合ログで空を確認し、非空ファイルの欠落とは区別して検証した。
署名付きログ URL の query は保存せず、認証情報は記録・納品物に含めない。

以下はレビュー用の照合結果であり、Redmine のチェック状態・status・done ratio を変更した記録ではない。

| 完了条件 | 照合結果 | 参照 |
| --- | --- | --- |
| C1 | 観測証拠あり。承認前実行・SHA/hash 不一致なし | §2–4、付録 A/B |
| C2 | 観測証拠あり。準備前後・標識・venv/pip・UID を記録 | §4–5、付録 B |
| C3 | 観測証拠あり。名前不在・基底拒否・別 venv 成功を分離 | §5、付録 B |
| C4 | 承認された必要ケースを整理。E01 限定 carry-in と後始末の未完了事項を明記 | §7、§10。最終判断は人間のレビュー |
| C5 | 全候補の前後・追加パス・ignore/target を比較 | §6、付録 B |
| C6 | 判断材料・証拠索引・main 照合を本書に整理。恒久反映はレビュー/マージ待ち | §9–13、付録 A/B |

## 13. 残る手続き

1. 人間がこの記録の内容・限界をレビューし、本ファイルだけを通常の作業 branch で commit、通常経路（ローカル → Git サーバー → GitHub）で反映して main にマージする。
2. 反映 commit、記録パス、最終完了判定を #5544 journal に残す。AI に Redmine 更新を依頼する場合は具体的な更新内容への別途承認を用いる。
3. #5544 完了と成果物版確定後、承認済みの M2 分担で #5545 へ進む。実験 branch の削除は証拠退避・main 反映の確認後。

## 付録 A. 全読み取りの証拠索引

各 candidate の job URL は §3。各読み取りの原文は
`evidence/<candidate>/<candidate>.log`、raw stream は
`evidence/<candidate>/readings/<candidate>/<reading>.stdout` / `.stderr`。
終了コードは `<candidate>.index.tsv` と照合済み。空 stream の扱いは §12 のとおり。
以下のコマンドは観測 helper が保存した shell-escaped 表記であり、ここで再実行する指示ではない。

### E01

結合ログ SHA-256: `537a64f39f8d25a4b0cf7f78b3c5ce1cf400b2b493b9616e4d102ff01731559e`。索引 SHA-256: `8135f9ab4bfefae9840091d600c5785e500364d1de97297ee86c5b09379551c3`。

| reading | exit | 実行コマンド |
| --- | --- | --- |
| id-user-before-preparation | 0 | `id -u` |
| uname-before-preparation | 0 | `uname -m` |
| os-release-before-preparation | 0 | `cat /etc/os-release` |
| which-python-before-preparation | 0 | `command -v python` |
| which-python3-before-preparation | 0 | `command -v python3` |
| which-pip-before-preparation | 0 | `command -v pip` |
| which-pip3-before-preparation | 0 | `command -v pip3` |
| which-git-before-preparation | 0 | `command -v git` |
| which-ssh-before-preparation | 0 | `command -v ssh` |
| which-yamllint-before-preparation | 1 | `command -v yamllint` |
| python3-version-before-preparation | 0 | `python3 -VV` |
| stdlib-before-preparation | 0 | `python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)` |
| venv-state-before-preparation | 0 | `python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)` |
| pip-version-before-preparation | 0 | `python3 -m pip --version` |
| marker-sysconfig-before-preparation | 2 | `ls -l /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED` |
| marker-usrlib-before-preparation | 0 | `/bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| marker-head-before-preparation | 0 | `/bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| candidate-role | 0 | `python3 /tmp/meas/check-candidate.py` |
| candidate-pip | 0 | `python3 -m pip --version` |
| revision-sha | 0 | `git rev-parse HEAD` |
| config-hash | 0 | `sha256sum .circleci/config.yml` |
| worktree-clean | 0 | `git status --porcelain` |
| revision-branch | 0 | `git rev-parse --abbrev-ref HEAD` |
| commit-subject | 0 | `git log -1 --pretty=%s` |
| pipeline | 0 | `/bin/bash -o pipefail -c printf\ \"pipeline=%s\ job=%s\ build_url=%s\ workflow=%s\\n\"\ \"\$\{MEAS_PIPELINE_NUMBER:-\}\"\ \"\$\{CIRCLE_JOB:-\}\"\ \"\$\{CIRCLE_BUILD_URL:-\}\"\ \"\$\{CIRCLE_WORKFLOW_ID:-\}\"` |
| install-sh-unpinned | 0 | `/bin/bash -o pipefail -c PARAM_VERSION=\"\"\ bash\ src/scripts/install.sh` |
| install-sh-pinned | 0 | `/bin/bash -o pipefail -c PARAM_VERSION=1.38.0\ bash\ src/scripts/install.sh` |
| pip-base-env | 0 | `python3 -m pip install yamllint==1.38.0` |
| yamllint-after-base-attempt | 0 | `/bin/bash -o pipefail -c command\ -v\ yamllint\ \&\&\ yamllint\ --version` |
| venv-create-attempt-1 | 0 | `python3 -m venv /tmp/meas/venv` |
| venv-state-after-attempt-1 | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/venv/bin\ 2\>\&1\;\ ls\ -l\ /tmp/meas/venv/pyvenv.cfg\ 2\>\&1` |
| venv-pip-after-attempt-1 | 0 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-without-pip | 0 | `python3 -m venv --without-pip /tmp/meas/venv-nopip` |
| ensurepip-importable | 0 | `python3 -c import\ ensurepip\;\ print\(ensurepip.__file__\)` |
| venv-pip-install | 0 | `/tmp/meas/venv/bin/python -m pip install yamllint==1.38.0` |
| venv-pip-version | 0 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-yamllint-version | 0 | `/tmp/meas/venv/bin/yamllint --version` |
| venv-prefix | 0 | `/tmp/meas/venv/bin/python -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.executable\)` |
| venv-marker | 2 | `/bin/bash -o pipefail -c ls\ -l\ \"\$\(/tmp/meas/venv/bin/python\ -c\ \"import\ sysconfig\;\ print\(sysconfig.get_path\(\\\"stdlib\\\"\)\)\"\)/EXTERNALLY-MANAGED\"` |
| inside-listing-before | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| inside-venv-create | 0 | `python3 -m venv /tmp/meas/fixtures/inside/venv-in-tree` |
| inside-venv-install | 0 | `/tmp/meas/fixtures/inside/venv-in-tree/bin/python -m pip install yamllint==1.38.0` |
| inside-listing-after | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| inside-listing-diff | 1 | `diff -u /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| inside-listing-added | 0 | `comm -13 /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| inside-listing-count | 0 | `wc -l /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| outside-listing-before | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| outside-venv-create | 0 | `python3 -m venv /tmp/meas/venv-outside` |
| outside-venv-install | 0 | `/tmp/meas/venv-outside/bin/python -m pip install yamllint==1.38.0` |
| outside-listing-after | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| outside-listing-diff | 0 | `diff -u /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| outside-listing-added | 0 | `comm -13 /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| outside-listing-count | 0 | `wc -l /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| listing-with-ignore | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ -d\ \"\{extends:\ relaxed\,\ ignore:\ \[venv-in-tree/\]\}\"\ --list-files\ .\ \\|\ sort` |
| listing-targets-only | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ tree\ \\|\ sort` |
| lint-whole-tree | 0 | `/tmp/meas/venv/bin/yamllint .` |
| venv-onto-nonempty-dir | 0 | `python3 -m venv /tmp/meas/place/nonempty` |
| venv-onto-regular-file | 1 | `python3 -m venv /tmp/meas/place/regular-file` |
| venv-onto-partial | 0 | `python3 -m venv /tmp/meas/place/partial` |
| venv-onto-complete | 0 | `python3 -m venv /tmp/meas/venv` |
| venv-complete-still-usable | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --version` |
| venv-created-twice | 0 | `/bin/bash -o pipefail -c python3\ -m\ venv\ /tmp/meas/place/twice\ \&\&\ python3\ -m\ venv\ /tmp/meas/place/twice` |
| venv-relative-path | 0 | `/bin/bash -o pipefail -c cd\ /tmp/meas/place\ \&\&\ python3\ -m\ venv\ ./relative\ \&\&\ ls\ -d\ /tmp/meas/place/relative` |
| venv-tilde-literal | 0 | `/bin/bash -o pipefail -c cd\ /tmp/meas/place\ \&\&\ python3\ -m\ venv\ \"~/meas-tilde\"` |
| venv-tilde-where | 0 | `ls -d /tmp/meas/place/~/meas-tilde` |
| venv-variable-literal | 0 | `python3 -m venv \$MEAS_PLACE/meas-var` |
| venv-variable-literal-where | 0 | `ls -d /tmp/meas/place/\$MEAS_PLACE/meas-var` |
| venv-variable-expanded | 0 | `python3 -m venv /tmp/meas/place/expanded-var` |
| venv-variable-expanded-where | 0 | `ls -d /tmp/meas/place/expanded-var` |
| place-listing | 0 | `/bin/bash -o pipefail -c ls\ -la\ /tmp/meas/place` |
| path-value | 0 | `/bin/bash -o pipefail -c printf\ \"PATH=%s\\n\"\ \"\$PATH\"` |
| path-resolution | 0 | `/bin/bash -o pipefail -c command\ -v\ yamllint\ \\|\\|\ echo\ ABSENT` |
| venv-executable | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/venv/bin/yamllint\ \&\&\ head\ -1\ /tmp/meas/venv/bin/yamllint` |
| venv-pip-show | 0 | `/tmp/meas/venv/bin/python -m pip show -f yamllint` |
| venv-module-file | 0 | `/tmp/meas/venv/bin/python -c import\ yamllint\;\ print\(yamllint.__file__\,\ yamllint.APP_VERSION\)` |
| venv-module-launch | 0 | `/tmp/meas/venv/bin/python -m yamllint --version` |
| main-not-touched | 0 | `/bin/bash -o pipefail -c cd\ \"\$\(cat\ /tmp/meas/repo_path\)\"\ \&\&\ git\ status\ --porcelain\ \&\&\ git\ diff\ --stat` |

### E02

結合ログ SHA-256: `60a2b3559ef3abf9607d6f7bb1d4606b3eac9eade84928721ca3aa39e7e569e7`。索引 SHA-256: `77bda5ae9f6362344bc5eafa5d7eacd98d22c0e842d48fc7c4cec0cb93d4c0ac`。

| reading | exit | 実行コマンド |
| --- | --- | --- |
| id-user-before-preparation | 0 | `id -u` |
| uname-before-preparation | 0 | `uname -m` |
| os-release-before-preparation | 0 | `cat /etc/os-release` |
| which-python-before-preparation | 0 | `command -v python` |
| which-python3-before-preparation | 0 | `command -v python3` |
| which-pip-before-preparation | 0 | `command -v pip` |
| which-pip3-before-preparation | 0 | `command -v pip3` |
| which-git-before-preparation | 0 | `command -v git` |
| which-ssh-before-preparation | 0 | `command -v ssh` |
| which-yamllint-before-preparation | 1 | `command -v yamllint` |
| python3-version-before-preparation | 0 | `python3 -VV` |
| stdlib-before-preparation | 0 | `python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)` |
| venv-state-before-preparation | 0 | `python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)` |
| pip-version-before-preparation | 0 | `python3 -m pip --version` |
| marker-sysconfig-before-preparation | 2 | `ls -l /home/circleci/.pyenv/versions/3.13.18/lib/python3.13/EXTERNALLY-MANAGED` |
| marker-usrlib-before-preparation | 2 | `/bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| marker-head-before-preparation | 1 | `/bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| candidate-role | 0 | `python3 /tmp/meas/check-candidate.py` |
| candidate-pip | 0 | `python3 -m pip --version` |
| revision-sha | 0 | `git rev-parse HEAD` |
| config-hash | 0 | `sha256sum .circleci/config.yml` |
| worktree-clean | 0 | `git status --porcelain` |
| revision-branch | 0 | `git rev-parse --abbrev-ref HEAD` |
| commit-subject | 0 | `git log -1 --pretty=%s` |
| pipeline | 0 | `/bin/bash -o pipefail -c printf\ \"pipeline=%s\ job=%s\ build_url=%s\ workflow=%s\\n\"\ \"\$\{MEAS_PIPELINE_NUMBER:-\}\"\ \"\$\{CIRCLE_JOB:-\}\"\ \"\$\{CIRCLE_BUILD_URL:-\}\"\ \"\$\{CIRCLE_WORKFLOW_ID:-\}\"` |
| install-sh-unpinned | 0 | `/bin/bash -o pipefail -c PARAM_VERSION=\"\"\ bash\ src/scripts/install.sh` |
| install-sh-pinned | 0 | `/bin/bash -o pipefail -c PARAM_VERSION=1.38.0\ bash\ src/scripts/install.sh` |
| pip-base-env | 0 | `python3 -m pip install yamllint==1.38.0` |
| yamllint-after-base-attempt | 0 | `/bin/bash -o pipefail -c command\ -v\ yamllint\ \&\&\ yamllint\ --version` |
| venv-create-attempt-1 | 0 | `python3 -m venv /tmp/meas/venv` |
| venv-state-after-attempt-1 | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/venv/bin\ 2\>\&1\;\ ls\ -l\ /tmp/meas/venv/pyvenv.cfg\ 2\>\&1` |
| venv-pip-after-attempt-1 | 0 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-without-pip | 0 | `python3 -m venv --without-pip /tmp/meas/venv-nopip` |
| ensurepip-importable | 0 | `python3 -c import\ ensurepip\;\ print\(ensurepip.__file__\)` |
| venv-pip-install | 0 | `/tmp/meas/venv/bin/python -m pip install yamllint==1.38.0` |
| venv-pip-version | 0 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-yamllint-version | 0 | `/tmp/meas/venv/bin/yamllint --version` |
| venv-prefix | 0 | `/tmp/meas/venv/bin/python -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.executable\)` |
| venv-marker | 2 | `/bin/bash -o pipefail -c ls\ -l\ \"\$\(/tmp/meas/venv/bin/python\ -c\ \"import\ sysconfig\;\ print\(sysconfig.get_path\(\\\"stdlib\\\"\)\)\"\)/EXTERNALLY-MANAGED\"` |
| inside-listing-before | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| inside-venv-create | 0 | `python3 -m venv /tmp/meas/fixtures/inside/venv-in-tree` |
| inside-venv-install | 0 | `/tmp/meas/fixtures/inside/venv-in-tree/bin/python -m pip install yamllint==1.38.0` |
| inside-listing-after | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| inside-listing-diff | 1 | `diff -u /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| inside-listing-added | 0 | `comm -13 /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| inside-listing-count | 0 | `wc -l /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| outside-listing-before | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| outside-venv-create | 0 | `python3 -m venv /tmp/meas/venv-outside` |
| outside-venv-install | 0 | `/tmp/meas/venv-outside/bin/python -m pip install yamllint==1.38.0` |
| outside-listing-after | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| outside-listing-diff | 0 | `diff -u /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| outside-listing-added | 0 | `comm -13 /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| outside-listing-count | 0 | `wc -l /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| listing-with-ignore | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ -d\ \"\{extends:\ relaxed\,\ ignore:\ \[venv-in-tree/\]\}\"\ --list-files\ .\ \\|\ sort` |
| listing-targets-only | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ tree\ \\|\ sort` |
| lint-whole-tree | 0 | `/tmp/meas/venv/bin/yamllint .` |
| venv-onto-nonempty-dir | 0 | `python3 -m venv /tmp/meas/place/nonempty` |
| venv-onto-regular-file | 1 | `python3 -m venv /tmp/meas/place/regular-file` |
| venv-onto-partial | 0 | `python3 -m venv /tmp/meas/place/partial` |
| venv-onto-complete | 0 | `python3 -m venv /tmp/meas/venv` |
| venv-complete-still-usable | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --version` |
| venv-created-twice | 0 | `/bin/bash -o pipefail -c python3\ -m\ venv\ /tmp/meas/place/twice\ \&\&\ python3\ -m\ venv\ /tmp/meas/place/twice` |
| venv-relative-path | 0 | `/bin/bash -o pipefail -c cd\ /tmp/meas/place\ \&\&\ python3\ -m\ venv\ ./relative\ \&\&\ ls\ -d\ /tmp/meas/place/relative` |
| venv-tilde-literal | 0 | `/bin/bash -o pipefail -c cd\ /tmp/meas/place\ \&\&\ python3\ -m\ venv\ \"~/meas-tilde\"` |
| venv-tilde-where | 0 | `ls -d /tmp/meas/place/~/meas-tilde` |
| venv-variable-literal | 0 | `python3 -m venv \$MEAS_PLACE/meas-var` |
| venv-variable-literal-where | 0 | `ls -d /tmp/meas/place/\$MEAS_PLACE/meas-var` |
| venv-variable-expanded | 0 | `python3 -m venv /tmp/meas/place/expanded-var` |
| venv-variable-expanded-where | 0 | `ls -d /tmp/meas/place/expanded-var` |
| place-listing | 0 | `/bin/bash -o pipefail -c ls\ -la\ /tmp/meas/place` |
| path-value | 0 | `/bin/bash -o pipefail -c printf\ \"PATH=%s\\n\"\ \"\$PATH\"` |
| path-resolution | 0 | `/bin/bash -o pipefail -c command\ -v\ yamllint\ \\|\\|\ echo\ ABSENT` |
| venv-executable | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/venv/bin/yamllint\ \&\&\ head\ -1\ /tmp/meas/venv/bin/yamllint` |
| venv-pip-show | 0 | `/tmp/meas/venv/bin/python -m pip show -f yamllint` |
| venv-module-file | 0 | `/tmp/meas/venv/bin/python -c import\ yamllint\;\ print\(yamllint.__file__\,\ yamllint.APP_VERSION\)` |
| venv-module-launch | 0 | `/tmp/meas/venv/bin/python -m yamllint --version` |
| main-not-touched | 0 | `/bin/bash -o pipefail -c cd\ \"\$\(cat\ /tmp/meas/repo_path\)\"\ \&\&\ git\ status\ --porcelain\ \&\&\ git\ diff\ --stat` |

### E03

結合ログ SHA-256: `24cb4ffee22e2989ba805f74155ed4f9ae30c452295324e9172680e70d5e8ac4`。索引 SHA-256: `7a32ab9a2f1784c5701883bdb59f95cd1a04c955c68bd7115fee37962250a068`。

| reading | exit | 実行コマンド |
| --- | --- | --- |
| id-user-before-preparation | 0 | `id -u` |
| uname-before-preparation | 0 | `uname -m` |
| os-release-before-preparation | 0 | `cat /etc/os-release` |
| which-python-before-preparation | 1 | `command -v python` |
| which-python3-before-preparation | 1 | `command -v python3` |
| which-pip-before-preparation | 1 | `command -v pip` |
| which-pip3-before-preparation | 1 | `command -v pip3` |
| which-git-before-preparation | 1 | `command -v git` |
| which-ssh-before-preparation | 1 | `command -v ssh` |
| which-yamllint-before-preparation | 1 | `command -v yamllint` |
| python3-version-before-preparation | 127 | `python3 -VV` |
| stdlib-before-preparation | 127 | `python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)` |
| venv-state-before-preparation | 127 | `python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)` |
| pip-version-before-preparation | 127 | `python3 -m pip --version` |
| marker-usrlib-before-preparation | 2 | `/bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| marker-head-before-preparation | 1 | `/bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| apt-update | 0 | `apt-get update` |
| apt-install-stage-a | 0 | `apt-get install -y --no-install-recommends python3 python3-pip git ca-certificates openssh-client` |
| apt-versions-stage-a | 0 | `dpkg-query -W -f \$\{Package\}\ \$\{Version\}\\n python3 python3-pip git` |
| venv-package-absent | 0 | `/bin/bash -o pipefail -c dpkg-query\ -W\ python3-venv` |
| id-user-after-preparation | 0 | `id -u` |
| uname-after-preparation | 0 | `uname -m` |
| os-release-after-preparation | 0 | `cat /etc/os-release` |
| which-python-after-preparation | 1 | `command -v python` |
| which-python3-after-preparation | 0 | `command -v python3` |
| which-pip-after-preparation | 0 | `command -v pip` |
| which-pip3-after-preparation | 0 | `command -v pip3` |
| which-git-after-preparation | 0 | `command -v git` |
| which-ssh-after-preparation | 0 | `command -v ssh` |
| which-yamllint-after-preparation | 1 | `command -v yamllint` |
| python3-version-after-preparation | 0 | `python3 -VV` |
| stdlib-after-preparation | 0 | `python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)` |
| venv-state-after-preparation | 0 | `python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)` |
| pip-version-after-preparation | 0 | `python3 -m pip --version` |
| marker-sysconfig-after-preparation | 2 | `ls -l /usr/lib/python3.10/EXTERNALLY-MANAGED` |
| marker-usrlib-after-preparation | 2 | `/bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| marker-head-after-preparation | 1 | `/bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| candidate-role | 0 | `python3 /tmp/meas/check-candidate.py` |
| candidate-pip | 0 | `python3 -m pip --version` |
| venv-packages-before-first-attempt | 0 | `/bin/bash -o pipefail -c dpkg-query\ -W\ -f=\'\$\{binary:Package\}\ \$\{db:Status-Status\}\\n\'\ \'python3\*-venv\'` |
| revision-sha | 0 | `git rev-parse HEAD` |
| config-hash | 0 | `sha256sum .circleci/config.yml` |
| worktree-clean | 0 | `git status --porcelain` |
| revision-branch | 0 | `git rev-parse --abbrev-ref HEAD` |
| commit-subject | 0 | `git log -1 --pretty=%s` |
| pipeline | 0 | `/bin/bash -o pipefail -c printf\ \"pipeline=%s\ job=%s\ build_url=%s\ workflow=%s\\n\"\ \"\$\{MEAS_PIPELINE_NUMBER:-\}\"\ \"\$\{CIRCLE_JOB:-\}\"\ \"\$\{CIRCLE_BUILD_URL:-\}\"\ \"\$\{CIRCLE_WORKFLOW_ID:-\}\"` |
| install-sh-unpinned | 127 | `/bin/bash -o pipefail -c PARAM_VERSION=\"\"\ bash\ src/scripts/install.sh` |
| install-sh-pinned | 127 | `/bin/bash -o pipefail -c PARAM_VERSION=1.38.0\ bash\ src/scripts/install.sh` |
| pip-base-env | 0 | `python3 -m pip install yamllint==1.38.0` |
| yamllint-after-base-attempt | 0 | `/bin/bash -o pipefail -c command\ -v\ yamllint\ \&\&\ yamllint\ --version` |
| venv-create-attempt-1 | 1 | `python3 -m venv /tmp/meas/venv` |
| venv-state-after-attempt-1 | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/venv/bin\ 2\>\&1\;\ ls\ -l\ /tmp/meas/venv/pyvenv.cfg\ 2\>\&1` |
| venv-pip-after-attempt-1 | 1 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-without-pip | 0 | `python3 -m venv --without-pip /tmp/meas/venv-nopip` |
| ensurepip-importable | 1 | `python3 -c import\ ensurepip\;\ print\(ensurepip.__file__\)` |
| partial-venv-kept | 0 | `/bin/bash -o pipefail -c test\ -e\ /tmp/meas/venv\ \&\&\ mv\ /tmp/meas/venv\ /tmp/meas/venv-partial\ \&\&\ ls\ -lR\ /tmp/meas/venv-partial\ \\|\ sed\ -n\ \"1\,40p\"` |
| apt-install-stage-b | 0 | `apt-get install -y --no-install-recommends python3-venv` |
| apt-versions-stage-b | 0 | `dpkg-query -W -f \$\{Package\}\ \$\{Version\}\\n python3-venv` |
| venv-create-attempt-2 | 0 | `python3 -m venv /tmp/meas/venv` |
| venv-pip-after-attempt-2 | 0 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-pip-install | 0 | `/tmp/meas/venv/bin/python -m pip install yamllint==1.38.0` |
| venv-pip-version | 0 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-yamllint-version | 0 | `/tmp/meas/venv/bin/yamllint --version` |
| venv-prefix | 0 | `/tmp/meas/venv/bin/python -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.executable\)` |
| venv-marker | 2 | `/bin/bash -o pipefail -c ls\ -l\ \"\$\(/tmp/meas/venv/bin/python\ -c\ \"import\ sysconfig\;\ print\(sysconfig.get_path\(\\\"stdlib\\\"\)\)\"\)/EXTERNALLY-MANAGED\"` |
| inside-listing-before | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| inside-venv-create | 0 | `python3 -m venv /tmp/meas/fixtures/inside/venv-in-tree` |
| inside-venv-install | 0 | `/tmp/meas/fixtures/inside/venv-in-tree/bin/python -m pip install yamllint==1.38.0` |
| inside-listing-after | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| inside-listing-diff | 1 | `diff -u /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| inside-listing-added | 0 | `comm -13 /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| inside-listing-count | 0 | `wc -l /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| outside-listing-before | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| outside-venv-create | 0 | `python3 -m venv /tmp/meas/venv-outside` |
| outside-venv-install | 0 | `/tmp/meas/venv-outside/bin/python -m pip install yamllint==1.38.0` |
| outside-listing-after | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| outside-listing-diff | 0 | `diff -u /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| outside-listing-added | 0 | `comm -13 /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| outside-listing-count | 0 | `wc -l /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| listing-with-ignore | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ -d\ \"\{extends:\ relaxed\,\ ignore:\ \[venv-in-tree/\]\}\"\ --list-files\ .\ \\|\ sort` |
| listing-targets-only | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ tree\ \\|\ sort` |
| lint-whole-tree | 0 | `/tmp/meas/venv/bin/yamllint .` |
| venv-onto-nonempty-dir | 0 | `python3 -m venv /tmp/meas/place/nonempty` |
| venv-onto-regular-file | 1 | `python3 -m venv /tmp/meas/place/regular-file` |
| venv-onto-partial | 0 | `python3 -m venv /tmp/meas/place/partial` |
| venv-onto-real-partial | 0 | `python3 -m venv /tmp/meas/venv-partial` |
| real-partial-pip | 0 | `/tmp/meas/venv-partial/bin/python -m pip --version` |
| venv-onto-complete | 0 | `python3 -m venv /tmp/meas/venv` |
| venv-complete-still-usable | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --version` |
| venv-created-twice | 0 | `/bin/bash -o pipefail -c python3\ -m\ venv\ /tmp/meas/place/twice\ \&\&\ python3\ -m\ venv\ /tmp/meas/place/twice` |
| venv-relative-path | 0 | `/bin/bash -o pipefail -c cd\ /tmp/meas/place\ \&\&\ python3\ -m\ venv\ ./relative\ \&\&\ ls\ -d\ /tmp/meas/place/relative` |
| venv-tilde-literal | 0 | `/bin/bash -o pipefail -c cd\ /tmp/meas/place\ \&\&\ python3\ -m\ venv\ \"~/meas-tilde\"` |
| venv-tilde-where | 0 | `ls -d /tmp/meas/place/~/meas-tilde` |
| venv-variable-literal | 0 | `python3 -m venv \$MEAS_PLACE/meas-var` |
| venv-variable-literal-where | 0 | `ls -d /tmp/meas/place/\$MEAS_PLACE/meas-var` |
| venv-variable-expanded | 0 | `python3 -m venv /tmp/meas/place/expanded-var` |
| venv-variable-expanded-where | 0 | `ls -d /tmp/meas/place/expanded-var` |
| place-listing | 0 | `/bin/bash -o pipefail -c ls\ -la\ /tmp/meas/place` |
| path-value | 0 | `/bin/bash -o pipefail -c printf\ \"PATH=%s\\n\"\ \"\$PATH\"` |
| path-resolution | 0 | `/bin/bash -o pipefail -c command\ -v\ yamllint\ \\|\\|\ echo\ ABSENT` |
| venv-executable | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/venv/bin/yamllint\ \&\&\ head\ -1\ /tmp/meas/venv/bin/yamllint` |
| venv-pip-show | 0 | `/tmp/meas/venv/bin/python -m pip show -f yamllint` |
| venv-module-file | 0 | `/tmp/meas/venv/bin/python -c import\ yamllint\;\ print\(yamllint.__file__\,\ yamllint.APP_VERSION\)` |
| venv-module-launch | 0 | `/tmp/meas/venv/bin/python -m yamllint --version` |
| main-not-touched | 0 | `/bin/bash -o pipefail -c cd\ \"\$\(cat\ /tmp/meas/repo_path\)\"\ \&\&\ git\ status\ --porcelain\ \&\&\ git\ diff\ --stat` |

### E04

結合ログ SHA-256: `67761819ab376a54664ab77eb49cb9a62ff9b08c66c78829cebf2a9e20ec2f50`。索引 SHA-256: `d7311d007857e06882cfcbe110804205b92b1fe694e837063f5282644faa7760`。

| reading | exit | 実行コマンド |
| --- | --- | --- |
| id-user-before-preparation | 0 | `id -u` |
| uname-before-preparation | 0 | `uname -m` |
| os-release-before-preparation | 0 | `cat /etc/os-release` |
| which-python-before-preparation | 1 | `command -v python` |
| which-python3-before-preparation | 1 | `command -v python3` |
| which-pip-before-preparation | 1 | `command -v pip` |
| which-pip3-before-preparation | 1 | `command -v pip3` |
| which-git-before-preparation | 1 | `command -v git` |
| which-ssh-before-preparation | 1 | `command -v ssh` |
| which-yamllint-before-preparation | 1 | `command -v yamllint` |
| python3-version-before-preparation | 127 | `python3 -VV` |
| stdlib-before-preparation | 127 | `python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)` |
| venv-state-before-preparation | 127 | `python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)` |
| pip-version-before-preparation | 127 | `python3 -m pip --version` |
| marker-usrlib-before-preparation | 2 | `/bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| marker-head-before-preparation | 1 | `/bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| apt-update | 0 | `apt-get update` |
| apt-install-stage-a | 0 | `apt-get install -y --no-install-recommends python3 python3-pip git ca-certificates openssh-client` |
| apt-versions-stage-a | 0 | `dpkg-query -W -f \$\{Package\}\ \$\{Version\}\\n python3 python3-pip git` |
| venv-package-absent | 0 | `/bin/bash -o pipefail -c dpkg-query\ -W\ python3-venv` |
| id-user-after-preparation | 0 | `id -u` |
| uname-after-preparation | 0 | `uname -m` |
| os-release-after-preparation | 0 | `cat /etc/os-release` |
| which-python-after-preparation | 1 | `command -v python` |
| which-python3-after-preparation | 0 | `command -v python3` |
| which-pip-after-preparation | 0 | `command -v pip` |
| which-pip3-after-preparation | 0 | `command -v pip3` |
| which-git-after-preparation | 0 | `command -v git` |
| which-ssh-after-preparation | 0 | `command -v ssh` |
| which-yamllint-after-preparation | 1 | `command -v yamllint` |
| python3-version-after-preparation | 0 | `python3 -VV` |
| stdlib-after-preparation | 0 | `python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)` |
| venv-state-after-preparation | 0 | `python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)` |
| pip-version-after-preparation | 0 | `python3 -m pip --version` |
| marker-sysconfig-after-preparation | 0 | `ls -l /usr/lib/python3.12/EXTERNALLY-MANAGED` |
| marker-usrlib-after-preparation | 0 | `/bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| marker-head-after-preparation | 0 | `/bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| candidate-role | 0 | `python3 /tmp/meas/check-candidate.py` |
| candidate-pip | 0 | `python3 -m pip --version` |
| venv-packages-before-first-attempt | 0 | `/bin/bash -o pipefail -c dpkg-query\ -W\ -f=\'\$\{binary:Package\}\ \$\{db:Status-Status\}\\n\'\ \'python3\*-venv\'` |
| revision-sha | 0 | `git rev-parse HEAD` |
| config-hash | 0 | `sha256sum .circleci/config.yml` |
| worktree-clean | 0 | `git status --porcelain` |
| revision-branch | 0 | `git rev-parse --abbrev-ref HEAD` |
| commit-subject | 0 | `git log -1 --pretty=%s` |
| pipeline | 0 | `/bin/bash -o pipefail -c printf\ \"pipeline=%s\ job=%s\ build_url=%s\ workflow=%s\\n\"\ \"\$\{MEAS_PIPELINE_NUMBER:-\}\"\ \"\$\{CIRCLE_JOB:-\}\"\ \"\$\{CIRCLE_BUILD_URL:-\}\"\ \"\$\{CIRCLE_WORKFLOW_ID:-\}\"` |
| install-sh-unpinned | 127 | `/bin/bash -o pipefail -c PARAM_VERSION=\"\"\ bash\ src/scripts/install.sh` |
| install-sh-pinned | 127 | `/bin/bash -o pipefail -c PARAM_VERSION=1.38.0\ bash\ src/scripts/install.sh` |
| pip-base-env | 1 | `python3 -m pip install yamllint==1.38.0` |
| yamllint-after-base-attempt | 1 | `/bin/bash -o pipefail -c command\ -v\ yamllint\ \&\&\ yamllint\ --version` |
| venv-create-attempt-1 | 1 | `python3 -m venv /tmp/meas/venv` |
| venv-state-after-attempt-1 | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/venv/bin\ 2\>\&1\;\ ls\ -l\ /tmp/meas/venv/pyvenv.cfg\ 2\>\&1` |
| venv-pip-after-attempt-1 | 1 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-without-pip | 0 | `python3 -m venv --without-pip /tmp/meas/venv-nopip` |
| ensurepip-importable | 1 | `python3 -c import\ ensurepip\;\ print\(ensurepip.__file__\)` |
| partial-venv-kept | 0 | `/bin/bash -o pipefail -c test\ -e\ /tmp/meas/venv\ \&\&\ mv\ /tmp/meas/venv\ /tmp/meas/venv-partial\ \&\&\ ls\ -lR\ /tmp/meas/venv-partial\ \\|\ sed\ -n\ \"1\,40p\"` |
| apt-install-stage-b | 0 | `apt-get install -y --no-install-recommends python3-venv` |
| apt-versions-stage-b | 0 | `dpkg-query -W -f \$\{Package\}\ \$\{Version\}\\n python3-venv` |
| venv-create-attempt-2 | 0 | `python3 -m venv /tmp/meas/venv` |
| venv-pip-after-attempt-2 | 0 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-pip-install | 0 | `/tmp/meas/venv/bin/python -m pip install yamllint==1.38.0` |
| venv-pip-version | 0 | `/tmp/meas/venv/bin/python -m pip --version` |
| venv-yamllint-version | 0 | `/tmp/meas/venv/bin/yamllint --version` |
| venv-prefix | 0 | `/tmp/meas/venv/bin/python -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.executable\)` |
| venv-marker | 0 | `/bin/bash -o pipefail -c ls\ -l\ \"\$\(/tmp/meas/venv/bin/python\ -c\ \"import\ sysconfig\;\ print\(sysconfig.get_path\(\\\"stdlib\\\"\)\)\"\)/EXTERNALLY-MANAGED\"` |
| inside-listing-before | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| inside-venv-create | 0 | `python3 -m venv /tmp/meas/fixtures/inside/venv-in-tree` |
| inside-venv-install | 0 | `/tmp/meas/fixtures/inside/venv-in-tree/bin/python -m pip install yamllint==1.38.0` |
| inside-listing-after | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| inside-listing-diff | 1 | `diff -u /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| inside-listing-added | 0 | `comm -13 /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| inside-listing-count | 0 | `wc -l /tmp/meas/listings/inside-before.txt /tmp/meas/listings/inside-after.txt` |
| outside-listing-before | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| outside-venv-create | 0 | `python3 -m venv /tmp/meas/venv-outside` |
| outside-venv-install | 0 | `/tmp/meas/venv-outside/bin/python -m pip install yamllint==1.38.0` |
| outside-listing-after | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ .\ \\|\ sort` |
| outside-listing-diff | 0 | `diff -u /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| outside-listing-added | 0 | `comm -13 /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| outside-listing-count | 0 | `wc -l /tmp/meas/listings/outside-before.txt /tmp/meas/listings/outside-after.txt` |
| listing-with-ignore | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ -d\ \"\{extends:\ relaxed\,\ ignore:\ \[venv-in-tree/\]\}\"\ --list-files\ .\ \\|\ sort` |
| listing-targets-only | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --list-files\ tree\ \\|\ sort` |
| lint-whole-tree | 0 | `/tmp/meas/venv/bin/yamllint .` |
| venv-onto-nonempty-dir | 0 | `python3 -m venv /tmp/meas/place/nonempty` |
| venv-onto-regular-file | 1 | `python3 -m venv /tmp/meas/place/regular-file` |
| venv-onto-partial | 0 | `python3 -m venv /tmp/meas/place/partial` |
| venv-onto-real-partial | 0 | `python3 -m venv /tmp/meas/venv-partial` |
| real-partial-pip | 0 | `/tmp/meas/venv-partial/bin/python -m pip --version` |
| venv-onto-complete | 0 | `python3 -m venv /tmp/meas/venv` |
| venv-complete-still-usable | 0 | `/bin/bash -o pipefail -c /tmp/meas/venv/bin/yamllint\ --version` |
| venv-created-twice | 0 | `/bin/bash -o pipefail -c python3\ -m\ venv\ /tmp/meas/place/twice\ \&\&\ python3\ -m\ venv\ /tmp/meas/place/twice` |
| venv-relative-path | 0 | `/bin/bash -o pipefail -c cd\ /tmp/meas/place\ \&\&\ python3\ -m\ venv\ ./relative\ \&\&\ ls\ -d\ /tmp/meas/place/relative` |
| venv-tilde-literal | 0 | `/bin/bash -o pipefail -c cd\ /tmp/meas/place\ \&\&\ python3\ -m\ venv\ \"~/meas-tilde\"` |
| venv-tilde-where | 0 | `ls -d /tmp/meas/place/~/meas-tilde` |
| venv-variable-literal | 0 | `python3 -m venv \$MEAS_PLACE/meas-var` |
| venv-variable-literal-where | 0 | `ls -d /tmp/meas/place/\$MEAS_PLACE/meas-var` |
| venv-variable-expanded | 0 | `python3 -m venv /tmp/meas/place/expanded-var` |
| venv-variable-expanded-where | 0 | `ls -d /tmp/meas/place/expanded-var` |
| place-listing | 0 | `/bin/bash -o pipefail -c ls\ -la\ /tmp/meas/place` |
| path-value | 0 | `/bin/bash -o pipefail -c printf\ \"PATH=%s\\n\"\ \"\$PATH\"` |
| path-resolution | 0 | `/bin/bash -o pipefail -c command\ -v\ yamllint\ \\|\\|\ echo\ ABSENT` |
| venv-executable | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/venv/bin/yamllint\ \&\&\ head\ -1\ /tmp/meas/venv/bin/yamllint` |
| venv-pip-show | 0 | `/tmp/meas/venv/bin/python -m pip show -f yamllint` |
| venv-module-file | 0 | `/tmp/meas/venv/bin/python -c import\ yamllint\;\ print\(yamllint.__file__\,\ yamllint.APP_VERSION\)` |
| venv-module-launch | 0 | `/tmp/meas/venv/bin/python -m yamllint --version` |
| main-not-touched | 0 | `/bin/bash -o pipefail -c cd\ \"\$\(cat\ /tmp/meas/repo_path\)\"\ \&\&\ git\ status\ --porcelain\ \&\&\ git\ diff\ --stat` |

### E01-carry-in-producer

結合ログ SHA-256: `54e53a42ce92c83ce825d4e86df2ad61bb878c42def570b117822c54435edd60`。索引 SHA-256: `f77e3897b693e028066f951cd4b0150312546f2570132f10b3504cf6ec7d0d9d`。

| reading | exit | 実行コマンド |
| --- | --- | --- |
| id-user-before-preparation | 0 | `id -u` |
| uname-before-preparation | 0 | `uname -m` |
| os-release-before-preparation | 0 | `cat /etc/os-release` |
| which-python-before-preparation | 0 | `command -v python` |
| which-python3-before-preparation | 0 | `command -v python3` |
| which-pip-before-preparation | 0 | `command -v pip` |
| which-pip3-before-preparation | 0 | `command -v pip3` |
| which-git-before-preparation | 0 | `command -v git` |
| which-ssh-before-preparation | 0 | `command -v ssh` |
| which-yamllint-before-preparation | 1 | `command -v yamllint` |
| python3-version-before-preparation | 0 | `python3 -VV` |
| stdlib-before-preparation | 0 | `python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)` |
| venv-state-before-preparation | 0 | `python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)` |
| pip-version-before-preparation | 0 | `python3 -m pip --version` |
| marker-sysconfig-before-preparation | 2 | `ls -l /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED` |
| marker-usrlib-before-preparation | 0 | `/bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| marker-head-before-preparation | 0 | `/bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| candidate-role | 0 | `python3 /tmp/meas/check-candidate.py` |
| candidate-pip | 0 | `python3 -m pip --version` |
| revision-sha | 0 | `git rev-parse HEAD` |
| config-hash | 0 | `sha256sum .circleci/config.yml` |
| worktree-clean | 0 | `git status --porcelain` |
| revision-branch | 0 | `git rev-parse --abbrev-ref HEAD` |
| commit-subject | 0 | `git log -1 --pretty=%s` |
| pipeline | 0 | `/bin/bash -o pipefail -c printf\ \"pipeline=%s\ job=%s\ build_url=%s\ workflow=%s\\n\"\ \"\$\{MEAS_PIPELINE_NUMBER:-\}\"\ \"\$\{CIRCLE_JOB:-\}\"\ \"\$\{CIRCLE_BUILD_URL:-\}\"\ \"\$\{CIRCLE_WORKFLOW_ID:-\}\"` |
| producer-venv | 0 | `python3 -m venv /tmp/meas/carry/venv` |
| producer-install | 0 | `/tmp/meas/carry/venv/bin/python -m pip install yamllint==1.38.0` |
| producer-version | 0 | `/tmp/meas/carry/venv/bin/yamllint --version` |
| producer-prefix | 0 | `/tmp/meas/carry/venv/bin/python -c import\ sys\;\ print\(sys.prefix\,\ sys.executable\)` |
| producer-cfg | 0 | `cat /tmp/meas/carry/venv/pyvenv.cfg` |

### E01-carry-in-consumer

結合ログ SHA-256: `31b202cd8befc77b47821bd1e8a4a1bbbb0fdb8239a3769f0982822e4a9fa0d2`。索引 SHA-256: `2ff10430efc22fd5c941c01cb6bfc2c056c8a687fb52e11639b7244445cf1448`。

| reading | exit | 実行コマンド |
| --- | --- | --- |
| id-user-before-preparation | 0 | `id -u` |
| uname-before-preparation | 0 | `uname -m` |
| os-release-before-preparation | 0 | `cat /etc/os-release` |
| which-python-before-preparation | 0 | `command -v python` |
| which-python3-before-preparation | 0 | `command -v python3` |
| which-pip-before-preparation | 0 | `command -v pip` |
| which-pip3-before-preparation | 0 | `command -v pip3` |
| which-git-before-preparation | 0 | `command -v git` |
| which-ssh-before-preparation | 0 | `command -v ssh` |
| which-yamllint-before-preparation | 1 | `command -v yamllint` |
| python3-version-before-preparation | 0 | `python3 -VV` |
| stdlib-before-preparation | 0 | `python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)` |
| venv-state-before-preparation | 0 | `python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)` |
| pip-version-before-preparation | 0 | `python3 -m pip --version` |
| marker-sysconfig-before-preparation | 2 | `ls -l /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED` |
| marker-usrlib-before-preparation | 0 | `/bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| marker-head-before-preparation | 0 | `/bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED` |
| candidate-role | 0 | `python3 /tmp/meas/check-candidate.py` |
| candidate-pip | 0 | `python3 -m pip --version` |
| revision-sha | 0 | `git rev-parse HEAD` |
| config-hash | 0 | `sha256sum .circleci/config.yml` |
| worktree-clean | 0 | `git status --porcelain` |
| revision-branch | 0 | `git rev-parse --abbrev-ref HEAD` |
| commit-subject | 0 | `git log -1 --pretty=%s` |
| pipeline | 0 | `/bin/bash -o pipefail -c printf\ \"pipeline=%s\ job=%s\ build_url=%s\ workflow=%s\\n\"\ \"\$\{MEAS_PIPELINE_NUMBER:-\}\"\ \"\$\{CIRCLE_JOB:-\}\"\ \"\$\{CIRCLE_BUILD_URL:-\}\"\ \"\$\{CIRCLE_WORKFLOW_ID:-\}\"` |
| carried-listing | 0 | `/bin/bash -o pipefail -c ls\ -l\ /tmp/meas/carried/venv/bin\ \\|\ sed\ -n\ \"1\,20p\"` |
| carried-cfg | 0 | `cat /tmp/meas/carried/venv/pyvenv.cfg` |
| carried-version | 127 | `/tmp/meas/carried/venv/bin/yamllint --version` |
| carried-prefix | 0 | `/tmp/meas/carried/venv/bin/python -c import\ sys\;\ print\(sys.prefix\,\ sys.executable\)` |
| carried-relocated | 127 | `/bin/bash -o pipefail -c cp\ -a\ /tmp/meas/carried/venv\ /tmp/meas/relocated\ \&\&\ /tmp/meas/relocated/bin/yamllint\ --version` |

## 付録 B. 判断に使用した観測値の埋め込み

後日の判断に必要な identity、標識、診断、prefix、配置・列挙・持ち込みを下記に保存する。
コマンドと exit は付録 A の同名 reading に対応する。`stdout: (empty)` / `stderr: (empty)` は空出力。
apt/pip の取得進捗や全依存ファイル一覧などは本書では省略し、生ログに保存した。
改行制御文字はこの表示用抜粋で通常改行に整え、行末の空白を除いた。生データのハッシュは元バイト列で計算した。

### E01

```text
[id-user-before-preparation] exit=0
stdout:
1001
stderr:
(empty)

[uname-before-preparation] exit=0
stdout:
x86_64
stderr:
(empty)

[os-release-before-preparation] exit=0
stdout:
PRETTY_NAME="Ubuntu 24.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.5 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
stderr:
(empty)

[which-python-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/python
stderr:
(empty)

[which-python3-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/python3
stderr:
(empty)

[which-pip-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/pip
stderr:
(empty)

[which-pip3-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/pip3
stderr:
(empty)

[which-git-before-preparation] exit=0
stdout:
/usr/bin/git
stderr:
(empty)

[which-ssh-before-preparation] exit=0
stdout:
/usr/bin/ssh
stderr:
(empty)

[which-yamllint-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[python3-version-before-preparation] exit=0
stdout:
Python 3.14.10 (main, Oct 26 2026, 22:11:46) [GCC 13.3.0]
stderr:
(empty)

[stdlib-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/versions/3.14.10/lib/python3.14
stderr:
(empty)

[venv-state-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/versions/3.14.10 /home/circleci/.pyenv/versions/3.14.10 False
stderr:
(empty)

[pip-version-before-preparation] exit=0
stdout:
pip 26.2.2 from /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/site-packages/pip (python 3.14)
stderr:
(empty)

[marker-sysconfig-before-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED': No such file or directory

[marker-usrlib-before-preparation] exit=0
stdout:
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
stderr:
(empty)

[marker-head-before-preparation] exit=0
stdout:
[externally-managed]
Error=To install Python packages system-wide, try apt install
 python3-xyz, where xyz is the package you are trying to
 install.

 If you wish to install a non-Debian-packaged Python package,
 create a virtual environment using python3 -m venv path/to/venv.
 Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
 sure you have python3-full installed.

 If you wish to install a non-Debian packaged Python application,
 it may be easiest to use pipx install xyz, which will manage a
 virtual environment for you. Make sure you have pipx installed.

 See /usr/share/doc/python3.12/README.venv for more information.
stderr:
(empty)

[candidate-role] exit=0
stdout:
{"in_venv": false, "marker_present": false, "os_id": "ubuntu", "os_version": "24.04", "python_present": true, "python_version": "3.14", "role": "E01"}
stderr:
(empty)

[candidate-pip] exit=0
stdout:
pip 26.2.2 from /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/site-packages/pip (python 3.14)
stderr:
(empty)

[yamllint-after-base-attempt] exit=0
stdout:
/home/circleci/.pyenv/shims/yamllint
yamllint 1.38.0
stderr:
(empty)

[venv-create-attempt-1] exit=0
stdout:
(empty)
stderr:
(empty)

[venv-state-after-attempt-1] exit=0
stdout:
total 36
-rw-r--r-- 1 circleci circleci 2154 Nov 17 13:10 activate
-rw-r--r-- 1 circleci circleci  944 Nov 17 13:10 activate.csh
-rw-r--r-- 1 circleci circleci 2174 Nov 17 13:10 activate.fish
-rw-r--r-- 1 circleci circleci 9031 Nov 17 13:10 Activate.ps1
-rwxr-xr-x 1 circleci circleci  179 Nov 17 13:10 pip
-rwxr-xr-x 1 circleci circleci  179 Nov 17 13:10 pip3
-rwxr-xr-x 1 circleci circleci  179 Nov 17 13:10 pip3.14
lrwxrwxrwx 1 circleci circleci    7 Nov 17 13:09 python -> python3
lrwxrwxrwx 1 circleci circleci   50 Nov 17 13:09 python3 -> /home/circleci/.pyenv/versions/3.14.10/bin/python3
lrwxrwxrwx 1 circleci circleci    7 Nov 17 13:09 python3.14 -> python3
lrwxrwxrwx 1 circleci circleci    7 Nov 17 13:09 𝜋thon -> python3
-rw-r--r-- 1 circleci circleci 256 Nov 17 13:09 /tmp/meas/venv/pyvenv.cfg
stderr:
(empty)

[venv-pip-after-attempt-1] exit=0
stdout:
pip 26.2.2 from /tmp/meas/venv/lib/python3.14/site-packages/pip (python 3.14)
stderr:
(empty)

[ensurepip-importable] exit=0
stdout:
/home/circleci/.pyenv/versions/3.14.10/lib/python3.14/ensurepip/__init__.py
stderr:
(empty)

[venv-pip-version] exit=0
stdout:
pip 26.2.2 from /tmp/meas/venv/lib/python3.14/site-packages/pip (python 3.14)
stderr:
(empty)

[venv-yamllint-version] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[venv-prefix] exit=0
stdout:
/tmp/meas/venv /home/circleci/.pyenv/versions/3.14.10 /tmp/meas/venv/bin/python
stderr:
(empty)

[venv-marker] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED': No such file or directory

[inside-listing-before] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./.yamllint
stderr:
(empty)

[inside-listing-after] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./venv-in-tree/lib/python3.14/site-packages/yamllint/conf/default.yaml
./venv-in-tree/lib/python3.14/site-packages/yamllint/conf/relaxed.yaml
./.yamllint
stderr:
(empty)

[inside-listing-diff] exit=1
stdout:
--- /tmp/meas/listings/inside-before.txt	2026-11-17 13:10:04.357146556 +0000
+++ /tmp/meas/listings/inside-after.txt	2026-11-17 13:10:08.858117234 +0000
@@ -1,3 +1,5 @@
 ./tree/ok.yaml
 ./tree/ok.yml
+./venv-in-tree/lib/python3.14/site-packages/yamllint/conf/default.yaml
+./venv-in-tree/lib/python3.14/site-packages/yamllint/conf/relaxed.yaml
 ./.yamllint
stderr:
(empty)

[inside-listing-added] exit=0
stdout:
./venv-in-tree/lib/python3.14/site-packages/yamllint/conf/default.yaml
./venv-in-tree/lib/python3.14/site-packages/yamllint/conf/relaxed.yaml
stderr:
(empty)

[outside-listing-before] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./.yamllint
stderr:
(empty)

[outside-listing-after] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./.yamllint
stderr:
(empty)

[listing-with-ignore] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./.yamllint
stderr:
(empty)

[listing-targets-only] exit=0
stdout:
tree/ok.yaml
tree/ok.yml
stderr:
(empty)

[venv-onto-regular-file] exit=1
stdout:
(empty)
stderr:
Error: Unable to create directory '/tmp/meas/place/regular-file'

[venv-complete-still-usable] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[venv-relative-path] exit=0
stdout:
/tmp/meas/place/relative
stderr:
(empty)

[venv-tilde-where] exit=0
stdout:
/tmp/meas/place/~/meas-tilde
stderr:
(empty)

[venv-variable-literal-where] exit=0
stdout:
/tmp/meas/place/$MEAS_PLACE/meas-var
stderr:
(empty)

[venv-variable-expanded-where] exit=0
stdout:
/tmp/meas/place/expanded-var
stderr:
(empty)

[path-value] exit=0
stdout:
PATH=/home/circleci/.pyenv/shims:/home/circleci/.pyenv/bin:/home/circleci/.poetry/bin:/home/circleci/bin:/home/circleci/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
stderr:
(empty)

[path-resolution] exit=0
stdout:
/home/circleci/.pyenv/shims/yamllint
stderr:
(empty)

[venv-executable] exit=0
stdout:
-rwxr-xr-x 1 circleci circleci 166 Nov 17 13:10 /tmp/meas/venv/bin/yamllint
#!/tmp/meas/venv/bin/python
stderr:
(empty)

[venv-module-file] exit=0
stdout:
/tmp/meas/venv/lib/python3.14/site-packages/yamllint/__init__.py 1.38.0
stderr:
(empty)

[venv-module-launch] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)
```

### E02

```text
[id-user-before-preparation] exit=0
stdout:
1001
stderr:
(empty)

[uname-before-preparation] exit=0
stdout:
x86_64
stderr:
(empty)

[os-release-before-preparation] exit=0
stdout:
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
stderr:
(empty)

[which-python-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/python
stderr:
(empty)

[which-python3-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/python3
stderr:
(empty)

[which-pip-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/pip
stderr:
(empty)

[which-pip3-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/pip3
stderr:
(empty)

[which-git-before-preparation] exit=0
stdout:
/usr/bin/git
stderr:
(empty)

[which-ssh-before-preparation] exit=0
stdout:
/usr/bin/ssh
stderr:
(empty)

[which-yamllint-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[python3-version-before-preparation] exit=0
stdout:
Python 3.13.18 (main, Oct 26 2026, 23:12:12) [GCC 11.4.0]
stderr:
(empty)

[stdlib-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/versions/3.13.18/lib/python3.13
stderr:
(empty)

[venv-state-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/versions/3.13.18 /home/circleci/.pyenv/versions/3.13.18 False
stderr:
(empty)

[pip-version-before-preparation] exit=0
stdout:
pip 26.2.2 from /home/circleci/.pyenv/versions/3.13.18/lib/python3.13/site-packages/pip (python 3.13)
stderr:
(empty)

[marker-sysconfig-before-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/home/circleci/.pyenv/versions/3.13.18/lib/python3.13/EXTERNALLY-MANAGED': No such file or directory

[marker-usrlib-before-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/usr/lib/python3*/EXTERNALLY-MANAGED': No such file or directory

[marker-head-before-preparation] exit=1
stdout:
(empty)
stderr:
head: cannot open '/usr/lib/python3*/EXTERNALLY-MANAGED' for reading: No such file or directory

[candidate-role] exit=0
stdout:
{"in_venv": false, "marker_present": false, "os_id": "ubuntu", "os_version": "22.04", "python_present": true, "python_version": "3.13", "role": "E02"}
stderr:
(empty)

[candidate-pip] exit=0
stdout:
pip 26.2.2 from /home/circleci/.pyenv/versions/3.13.18/lib/python3.13/site-packages/pip (python 3.13)
stderr:
(empty)

[yamllint-after-base-attempt] exit=0
stdout:
/home/circleci/.pyenv/shims/yamllint
yamllint 1.38.0
stderr:
(empty)

[venv-create-attempt-1] exit=0
stdout:
(empty)
stderr:
(empty)

[venv-state-after-attempt-1] exit=0
stdout:
total 36
-rw-r--r-- 1 circleci circleci 2154 Nov 17 13:10 activate
-rw-r--r-- 1 circleci circleci  944 Nov 17 13:10 activate.csh
-rw-r--r-- 1 circleci circleci 2174 Nov 17 13:10 activate.fish
-rw-r--r-- 1 circleci circleci 9031 Nov 17 13:10 Activate.ps1
-rwxr-xr-x 1 circleci circleci  179 Nov 17 13:10 pip
-rwxr-xr-x 1 circleci circleci  179 Nov 17 13:10 pip3
-rwxr-xr-x 1 circleci circleci  179 Nov 17 13:10 pip3.13
lrwxrwxrwx 1 circleci circleci    7 Nov 17 13:09 python -> python3
lrwxrwxrwx 1 circleci circleci   50 Nov 17 13:09 python3 -> /home/circleci/.pyenv/versions/3.13.18/bin/python3
lrwxrwxrwx 1 circleci circleci    7 Nov 17 13:09 python3.13 -> python3
-rw-r--r-- 1 circleci circleci 256 Nov 17 13:09 /tmp/meas/venv/pyvenv.cfg
stderr:
(empty)

[venv-pip-after-attempt-1] exit=0
stdout:
pip 26.2.2 from /tmp/meas/venv/lib/python3.13/site-packages/pip (python 3.13)
stderr:
(empty)

[ensurepip-importable] exit=0
stdout:
/home/circleci/.pyenv/versions/3.13.18/lib/python3.13/ensurepip/__init__.py
stderr:
(empty)

[venv-pip-version] exit=0
stdout:
pip 26.2.2 from /tmp/meas/venv/lib/python3.13/site-packages/pip (python 3.13)
stderr:
(empty)

[venv-yamllint-version] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[venv-prefix] exit=0
stdout:
/tmp/meas/venv /home/circleci/.pyenv/versions/3.13.18 /tmp/meas/venv/bin/python
stderr:
(empty)

[venv-marker] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/home/circleci/.pyenv/versions/3.13.18/lib/python3.13/EXTERNALLY-MANAGED': No such file or directory

[inside-listing-before] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./.yamllint
stderr:
(empty)

[inside-listing-after] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./venv-in-tree/lib/python3.13/site-packages/yamllint/conf/default.yaml
./venv-in-tree/lib/python3.13/site-packages/yamllint/conf/relaxed.yaml
./.yamllint
stderr:
(empty)

[inside-listing-diff] exit=1
stdout:
--- /tmp/meas/listings/inside-before.txt	2026-11-17 13:10:03.985725629 +0000
+++ /tmp/meas/listings/inside-after.txt	2026-11-17 13:10:08.530495183 +0000
@@ -1,3 +1,5 @@
 ./tree/ok.yaml
 ./tree/ok.yml
+./venv-in-tree/lib/python3.13/site-packages/yamllint/conf/default.yaml
+./venv-in-tree/lib/python3.13/site-packages/yamllint/conf/relaxed.yaml
 ./.yamllint
stderr:
(empty)

[inside-listing-added] exit=0
stdout:
./venv-in-tree/lib/python3.13/site-packages/yamllint/conf/default.yaml
./venv-in-tree/lib/python3.13/site-packages/yamllint/conf/relaxed.yaml
stderr:
(empty)

[outside-listing-before] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./.yamllint
stderr:
(empty)

[outside-listing-after] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./.yamllint
stderr:
(empty)

[listing-with-ignore] exit=0
stdout:
./tree/ok.yaml
./tree/ok.yml
./.yamllint
stderr:
(empty)

[listing-targets-only] exit=0
stdout:
tree/ok.yaml
tree/ok.yml
stderr:
(empty)

[venv-onto-regular-file] exit=1
stdout:
(empty)
stderr:
Error: Unable to create directory '/tmp/meas/place/regular-file'

[venv-complete-still-usable] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[venv-relative-path] exit=0
stdout:
/tmp/meas/place/relative
stderr:
(empty)

[venv-tilde-where] exit=0
stdout:
/tmp/meas/place/~/meas-tilde
stderr:
(empty)

[venv-variable-literal-where] exit=0
stdout:
/tmp/meas/place/$MEAS_PLACE/meas-var
stderr:
(empty)

[venv-variable-expanded-where] exit=0
stdout:
/tmp/meas/place/expanded-var
stderr:
(empty)

[path-value] exit=0
stdout:
PATH=/home/circleci/.pyenv/shims:/home/circleci/.pyenv/bin:/home/circleci/.poetry/bin:/home/circleci/bin:/home/circleci/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
stderr:
(empty)

[path-resolution] exit=0
stdout:
/home/circleci/.pyenv/shims/yamllint
stderr:
(empty)

[venv-executable] exit=0
stdout:
-rwxr-xr-x 1 circleci circleci 166 Nov 17 13:10 /tmp/meas/venv/bin/yamllint
#!/tmp/meas/venv/bin/python
stderr:
(empty)

[venv-module-file] exit=0
stdout:
/tmp/meas/venv/lib/python3.13/site-packages/yamllint/__init__.py 1.38.0
stderr:
(empty)

[venv-module-launch] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)
```

### E03

```text
[id-user-before-preparation] exit=0
stdout:
0
stderr:
(empty)

[uname-before-preparation] exit=0
stdout:
x86_64
stderr:
(empty)

[os-release-before-preparation] exit=0
stdout:
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
stderr:
(empty)

[which-python-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-python3-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-pip-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-pip3-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-git-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-ssh-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-yamllint-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[python3-version-before-preparation] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: python3: command not found

[stdlib-before-preparation] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: python3: command not found

[venv-state-before-preparation] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: python3: command not found

[pip-version-before-preparation] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: python3: command not found

[marker-usrlib-before-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/usr/lib/python3*/EXTERNALLY-MANAGED': No such file or directory

[marker-head-before-preparation] exit=1
stdout:
(empty)
stderr:
head: cannot open '/usr/lib/python3*/EXTERNALLY-MANAGED' for reading: No such file or directory

[apt-versions-stage-a] exit=0
stdout:
git 1:2.34.1-1ubuntu1.18
python3 3.10.6-1~22.04.1
python3-pip 22.0.2+dfsg-1ubuntu0.7
stderr:
(empty)

[id-user-after-preparation] exit=0
stdout:
0
stderr:
(empty)

[uname-after-preparation] exit=0
stdout:
x86_64
stderr:
(empty)

[os-release-after-preparation] exit=0
stdout:
PRETTY_NAME="Ubuntu 22.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="22.04"
VERSION="22.04.5 LTS (Jammy Jellyfish)"
VERSION_CODENAME=jammy
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=jammy
stderr:
(empty)

[which-python-after-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-python3-after-preparation] exit=0
stdout:
/usr/bin/python3
stderr:
(empty)

[which-pip-after-preparation] exit=0
stdout:
/usr/bin/pip
stderr:
(empty)

[which-pip3-after-preparation] exit=0
stdout:
/usr/bin/pip3
stderr:
(empty)

[which-git-after-preparation] exit=0
stdout:
/usr/bin/git
stderr:
(empty)

[which-ssh-after-preparation] exit=0
stdout:
/usr/bin/ssh
stderr:
(empty)

[which-yamllint-after-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[python3-version-after-preparation] exit=0
stdout:
Python 3.10.12 (main, Aug 31 2026, 10:18:17) [GCC 11.4.0]
stderr:
(empty)

[stdlib-after-preparation] exit=0
stdout:
/usr/lib/python3.10
stderr:
(empty)

[venv-state-after-preparation] exit=0
stdout:
/usr /usr False
stderr:
(empty)

[pip-version-after-preparation] exit=0
stdout:
pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)
stderr:
(empty)

[marker-sysconfig-after-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/usr/lib/python3.10/EXTERNALLY-MANAGED': No such file or directory

[marker-usrlib-after-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/usr/lib/python3*/EXTERNALLY-MANAGED': No such file or directory

[marker-head-after-preparation] exit=1
stdout:
(empty)
stderr:
head: cannot open '/usr/lib/python3*/EXTERNALLY-MANAGED' for reading: No such file or directory

[candidate-role] exit=0
stdout:
{"in_venv": false, "marker_present": false, "os_id": "ubuntu", "os_version": "22.04", "python_present": false, "python_version": "3.10", "role": "E03"}
stderr:
(empty)

[candidate-pip] exit=0
stdout:
pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)
stderr:
(empty)

[venv-packages-before-first-attempt] exit=0
stdout:
python3-venv not-installed
python3.10-venv not-installed
stderr:
(empty)

[install-sh-unpinned] exit=127
stdout:
(empty)
stderr:
src/scripts/install.sh: line 8: python: command not found

[install-sh-pinned] exit=127
stdout:
(empty)
stderr:
src/scripts/install.sh: line 6: python: command not found

[yamllint-after-base-attempt] exit=0
stdout:
/usr/local/bin/yamllint
yamllint 1.38.0
stderr:
(empty)

[venv-create-attempt-1] exit=1
stdout:
The virtual environment was not created successfully because ensurepip is not
available.  On Debian/Ubuntu systems, you need to install the python3-venv
package using the following command.

    apt install python3.10-venv

You may need to use sudo with that command.  After installing the python3-venv
package, recreate your virtual environment.

Failing command: /tmp/meas/venv/bin/python3

stderr:
(empty)

[venv-state-after-attempt-1] exit=0
stdout:
total 0
lrwxrwxrwx 1 root root  7 Nov 17 13:10 python -> python3
lrwxrwxrwx 1 root root 16 Nov 17 13:10 python3 -> /usr/bin/python3
lrwxrwxrwx 1 root root  7 Nov 17 13:10 python3.10 -> python3
-rw-r--r-- 1 root root 71 Nov 17 13:10 /tmp/meas/venv/pyvenv.cfg
stderr:
(empty)

[venv-pip-after-attempt-1] exit=1
stdout:
(empty)
stderr:
/tmp/meas/venv/bin/python: No module named pip

[ensurepip-importable] exit=1
stdout:
(empty)
stderr:
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'ensurepip'

[apt-versions-stage-b] exit=0
stdout:
python3-venv 3.10.6-1~22.04.1
stderr:
(empty)

[venv-pip-after-attempt-2] exit=0
stdout:
pip 22.0.2 from /tmp/meas/venv/lib/python3.10/site-packages/pip (python 3.10)
stderr:
(empty)

[venv-pip-version] exit=0
stdout:
pip 22.0.2 from /tmp/meas/venv/lib/python3.10/site-packages/pip (python 3.10)
stderr:
(empty)

[venv-yamllint-version] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[venv-prefix] exit=0
stdout:
/tmp/meas/venv /usr /tmp/meas/venv/bin/python
stderr:
(empty)

[venv-marker] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/usr/lib/python3.10/EXTERNALLY-MANAGED': No such file or directory

[inside-listing-before] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
stderr:
(empty)

[inside-listing-after] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
./venv-in-tree/lib/python3.10/site-packages/yamllint/conf/default.yaml
./venv-in-tree/lib/python3.10/site-packages/yamllint/conf/relaxed.yaml
stderr:
(empty)

[inside-listing-diff] exit=1
stdout:
--- /tmp/meas/listings/inside-before.txt	2026-11-17 13:10:27.787266893 +0000
+++ /tmp/meas/listings/inside-after.txt	2026-11-17 13:10:32.336073503 +0000
@@ -1,3 +1,5 @@
 ./.yamllint
 ./tree/ok.yaml
 ./tree/ok.yml
+./venv-in-tree/lib/python3.10/site-packages/yamllint/conf/default.yaml
+./venv-in-tree/lib/python3.10/site-packages/yamllint/conf/relaxed.yaml
stderr:
(empty)

[inside-listing-added] exit=0
stdout:
./venv-in-tree/lib/python3.10/site-packages/yamllint/conf/default.yaml
./venv-in-tree/lib/python3.10/site-packages/yamllint/conf/relaxed.yaml
stderr:
(empty)

[outside-listing-before] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
stderr:
(empty)

[outside-listing-after] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
stderr:
(empty)

[listing-with-ignore] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
stderr:
(empty)

[listing-targets-only] exit=0
stdout:
tree/ok.yaml
tree/ok.yml
stderr:
(empty)

[venv-onto-regular-file] exit=1
stdout:
(empty)
stderr:
Error: Unable to create directory '/tmp/meas/place/regular-file'

[real-partial-pip] exit=0
stdout:
pip 22.0.2 from /tmp/meas/venv-partial/lib/python3.10/site-packages/pip (python 3.10)
stderr:
(empty)

[venv-complete-still-usable] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[venv-relative-path] exit=0
stdout:
/tmp/meas/place/relative
stderr:
(empty)

[venv-tilde-where] exit=0
stdout:
/tmp/meas/place/~/meas-tilde
stderr:
(empty)

[venv-variable-literal-where] exit=0
stdout:
/tmp/meas/place/$MEAS_PLACE/meas-var
stderr:
(empty)

[venv-variable-expanded-where] exit=0
stdout:
/tmp/meas/place/expanded-var
stderr:
(empty)

[path-value] exit=0
stdout:
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
stderr:
(empty)

[path-resolution] exit=0
stdout:
/usr/local/bin/yamllint
stderr:
(empty)

[venv-executable] exit=0
stdout:
-rwxr-xr-x 1 root root 218 Nov 17 13:10 /tmp/meas/venv/bin/yamllint
#!/tmp/meas/venv/bin/python
stderr:
(empty)

[venv-module-file] exit=0
stdout:
/tmp/meas/venv/lib/python3.10/site-packages/yamllint/__init__.py 1.38.0
stderr:
(empty)

[venv-module-launch] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)
```

### E04

```text
[id-user-before-preparation] exit=0
stdout:
0
stderr:
(empty)

[uname-before-preparation] exit=0
stdout:
x86_64
stderr:
(empty)

[os-release-before-preparation] exit=0
stdout:
PRETTY_NAME="Ubuntu 24.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.5 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
stderr:
(empty)

[which-python-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-python3-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-pip-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-pip3-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-git-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-ssh-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-yamllint-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[python3-version-before-preparation] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: python3: command not found

[stdlib-before-preparation] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: python3: command not found

[venv-state-before-preparation] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: python3: command not found

[pip-version-before-preparation] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: python3: command not found

[marker-usrlib-before-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/usr/lib/python3*/EXTERNALLY-MANAGED': No such file or directory

[marker-head-before-preparation] exit=1
stdout:
(empty)
stderr:
head: cannot open '/usr/lib/python3*/EXTERNALLY-MANAGED' for reading: No such file or directory

[apt-versions-stage-a] exit=0
stdout:
git 1:2.43.0-1ubuntu7.4
python3 3.12.3-0ubuntu2.1
python3-pip 24.0+dfsg-1ubuntu1.3
stderr:
(empty)

[id-user-after-preparation] exit=0
stdout:
0
stderr:
(empty)

[uname-after-preparation] exit=0
stdout:
x86_64
stderr:
(empty)

[os-release-after-preparation] exit=0
stdout:
PRETTY_NAME="Ubuntu 24.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.5 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
stderr:
(empty)

[which-python-after-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[which-python3-after-preparation] exit=0
stdout:
/usr/bin/python3
stderr:
(empty)

[which-pip-after-preparation] exit=0
stdout:
/usr/bin/pip
stderr:
(empty)

[which-pip3-after-preparation] exit=0
stdout:
/usr/bin/pip3
stderr:
(empty)

[which-git-after-preparation] exit=0
stdout:
/usr/bin/git
stderr:
(empty)

[which-ssh-after-preparation] exit=0
stdout:
/usr/bin/ssh
stderr:
(empty)

[which-yamllint-after-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[python3-version-after-preparation] exit=0
stdout:
Python 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]
stderr:
(empty)

[stdlib-after-preparation] exit=0
stdout:
/usr/lib/python3.12
stderr:
(empty)

[venv-state-after-preparation] exit=0
stdout:
/usr /usr False
stderr:
(empty)

[pip-version-after-preparation] exit=0
stdout:
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)
stderr:
(empty)

[marker-sysconfig-after-preparation] exit=0
stdout:
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
stderr:
(empty)

[marker-usrlib-after-preparation] exit=0
stdout:
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
stderr:
(empty)

[marker-head-after-preparation] exit=0
stdout:
[externally-managed]
Error=To install Python packages system-wide, try apt install
 python3-xyz, where xyz is the package you are trying to
 install.

 If you wish to install a non-Debian-packaged Python package,
 create a virtual environment using python3 -m venv path/to/venv.
 Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
 sure you have python3-full installed.

 If you wish to install a non-Debian packaged Python application,
 it may be easiest to use pipx install xyz, which will manage a
 virtual environment for you. Make sure you have pipx installed.

 See /usr/share/doc/python3.12/README.venv for more information.
stderr:
(empty)

[candidate-role] exit=0
stdout:
{"in_venv": false, "marker_present": true, "os_id": "ubuntu", "os_version": "24.04", "python_present": false, "python_version": "3.12", "role": "E04"}
stderr:
(empty)

[candidate-pip] exit=0
stdout:
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)
stderr:
(empty)

[venv-packages-before-first-attempt] exit=0
stdout:
python3-venv not-installed
python3.12-venv not-installed
stderr:
(empty)

[install-sh-unpinned] exit=127
stdout:
(empty)
stderr:
src/scripts/install.sh: line 8: python: command not found

[install-sh-pinned] exit=127
stdout:
(empty)
stderr:
src/scripts/install.sh: line 6: python: command not found

[pip-base-env] exit=1
stdout:
(empty)
stderr:
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.

    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
    Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
    sure you have python3-full installed.

    If you wish to install a non-Debian packaged Python application,
    it may be easiest to use pipx install xyz, which will manage a
    virtual environment for you. Make sure you have pipx installed.

    See /usr/share/doc/python3.12/README.venv for more information.

note: If you believe this is a mistake, please contact your Python installation or OS distribution provider. You can override this, at the risk of breaking your Python installation or OS, by passing --break-system-packages.
hint: See PEP 668 for the detailed specification.

[yamllint-after-base-attempt] exit=1
stdout:
(empty)
stderr:
(empty)

[venv-create-attempt-1] exit=1
stdout:
The virtual environment was not created successfully because ensurepip is not
available.  On Debian/Ubuntu systems, you need to install the python3-venv
package using the following command.

    apt install python3.12-venv

You may need to use sudo with that command.  After installing the python3-venv
package, recreate your virtual environment.

Failing command: /tmp/meas/venv/bin/python3

stderr:
(empty)

[venv-state-after-attempt-1] exit=0
stdout:
total 0
lrwxrwxrwx 1 root root  7 Nov 17 13:10 python -> python3
lrwxrwxrwx 1 root root 16 Nov 17 13:10 python3 -> /usr/bin/python3
lrwxrwxrwx 1 root root  7 Nov 17 13:10 python3.12 -> python3
-rw-r--r-- 1 root root 153 Nov 17 13:10 /tmp/meas/venv/pyvenv.cfg
stderr:
(empty)

[venv-pip-after-attempt-1] exit=1
stdout:
(empty)
stderr:
/tmp/meas/venv/bin/python: No module named pip

[ensurepip-importable] exit=1
stdout:
(empty)
stderr:
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'ensurepip'

[apt-versions-stage-b] exit=0
stdout:
python3-venv 3.12.3-0ubuntu2.1
stderr:
(empty)

[venv-pip-after-attempt-2] exit=0
stdout:
pip 24.0 from /tmp/meas/venv/lib/python3.12/site-packages/pip (python 3.12)
stderr:
(empty)

[venv-pip-version] exit=0
stdout:
pip 24.0 from /tmp/meas/venv/lib/python3.12/site-packages/pip (python 3.12)
stderr:
(empty)

[venv-yamllint-version] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[venv-prefix] exit=0
stdout:
/tmp/meas/venv /usr /tmp/meas/venv/bin/python
stderr:
(empty)

[venv-marker] exit=0
stdout:
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
stderr:
(empty)

[inside-listing-before] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
stderr:
(empty)

[inside-listing-after] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
./venv-in-tree/lib/python3.12/site-packages/yamllint/conf/default.yaml
./venv-in-tree/lib/python3.12/site-packages/yamllint/conf/relaxed.yaml
stderr:
(empty)

[inside-listing-diff] exit=1
stdout:
--- /tmp/meas/listings/inside-before.txt	2026-11-17 13:10:22.874963120 +0000
+++ /tmp/meas/listings/inside-after.txt	2026-11-17 13:10:28.046747103 +0000
@@ -1,3 +1,5 @@
 ./.yamllint
 ./tree/ok.yaml
 ./tree/ok.yml
+./venv-in-tree/lib/python3.12/site-packages/yamllint/conf/default.yaml
+./venv-in-tree/lib/python3.12/site-packages/yamllint/conf/relaxed.yaml
stderr:
(empty)

[inside-listing-added] exit=0
stdout:
./venv-in-tree/lib/python3.12/site-packages/yamllint/conf/default.yaml
./venv-in-tree/lib/python3.12/site-packages/yamllint/conf/relaxed.yaml
stderr:
(empty)

[outside-listing-before] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
stderr:
(empty)

[outside-listing-after] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
stderr:
(empty)

[listing-with-ignore] exit=0
stdout:
./.yamllint
./tree/ok.yaml
./tree/ok.yml
stderr:
(empty)

[listing-targets-only] exit=0
stdout:
tree/ok.yaml
tree/ok.yml
stderr:
(empty)

[venv-onto-regular-file] exit=1
stdout:
(empty)
stderr:
Error: Unable to create directory '/tmp/meas/place/regular-file'

[real-partial-pip] exit=0
stdout:
pip 24.0 from /tmp/meas/venv-partial/lib/python3.12/site-packages/pip (python 3.12)
stderr:
(empty)

[venv-complete-still-usable] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[venv-relative-path] exit=0
stdout:
/tmp/meas/place/relative
stderr:
(empty)

[venv-tilde-where] exit=0
stdout:
/tmp/meas/place/~/meas-tilde
stderr:
(empty)

[venv-variable-literal-where] exit=0
stdout:
/tmp/meas/place/$MEAS_PLACE/meas-var
stderr:
(empty)

[venv-variable-expanded-where] exit=0
stdout:
/tmp/meas/place/expanded-var
stderr:
(empty)

[path-value] exit=0
stdout:
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
stderr:
(empty)

[path-resolution] exit=0
stdout:
ABSENT
stderr:
(empty)

[venv-executable] exit=0
stdout:
-rwxr-xr-x 1 root root 218 Nov 17 13:10 /tmp/meas/venv/bin/yamllint
#!/tmp/meas/venv/bin/python
stderr:
(empty)

[venv-module-file] exit=0
stdout:
/tmp/meas/venv/lib/python3.12/site-packages/yamllint/__init__.py 1.38.0
stderr:
(empty)

[venv-module-launch] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)
```

### E01-carry-in-producer

```text
[id-user-before-preparation] exit=0
stdout:
1001
stderr:
(empty)

[uname-before-preparation] exit=0
stdout:
x86_64
stderr:
(empty)

[os-release-before-preparation] exit=0
stdout:
PRETTY_NAME="Ubuntu 24.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.5 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
stderr:
(empty)

[which-python-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/python
stderr:
(empty)

[which-python3-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/python3
stderr:
(empty)

[which-pip-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/pip
stderr:
(empty)

[which-pip3-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/pip3
stderr:
(empty)

[which-git-before-preparation] exit=0
stdout:
/usr/bin/git
stderr:
(empty)

[which-ssh-before-preparation] exit=0
stdout:
/usr/bin/ssh
stderr:
(empty)

[which-yamllint-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[python3-version-before-preparation] exit=0
stdout:
Python 3.14.10 (main, Oct 26 2026, 22:11:46) [GCC 13.3.0]
stderr:
(empty)

[stdlib-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/versions/3.14.10/lib/python3.14
stderr:
(empty)

[venv-state-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/versions/3.14.10 /home/circleci/.pyenv/versions/3.14.10 False
stderr:
(empty)

[pip-version-before-preparation] exit=0
stdout:
pip 26.2.2 from /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/site-packages/pip (python 3.14)
stderr:
(empty)

[marker-sysconfig-before-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED': No such file or directory

[marker-usrlib-before-preparation] exit=0
stdout:
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
stderr:
(empty)

[marker-head-before-preparation] exit=0
stdout:
[externally-managed]
Error=To install Python packages system-wide, try apt install
 python3-xyz, where xyz is the package you are trying to
 install.

 If you wish to install a non-Debian-packaged Python package,
 create a virtual environment using python3 -m venv path/to/venv.
 Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
 sure you have python3-full installed.

 If you wish to install a non-Debian packaged Python application,
 it may be easiest to use pipx install xyz, which will manage a
 virtual environment for you. Make sure you have pipx installed.

 See /usr/share/doc/python3.12/README.venv for more information.
stderr:
(empty)

[candidate-role] exit=0
stdout:
{"in_venv": false, "marker_present": false, "os_id": "ubuntu", "os_version": "24.04", "python_present": true, "python_version": "3.14", "role": "E01"}
stderr:
(empty)

[candidate-pip] exit=0
stdout:
pip 26.2.2 from /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/site-packages/pip (python 3.14)
stderr:
(empty)

[producer-version] exit=0
stdout:
yamllint 1.38.0
stderr:
(empty)

[producer-prefix] exit=0
stdout:
/tmp/meas/carry/venv /tmp/meas/carry/venv/bin/python
stderr:
(empty)

[producer-cfg] exit=0
stdout:
home = /home/circleci/.pyenv/versions/3.14.10/bin
include-system-site-packages = false
version = 3.14.10
executable = /home/circleci/.pyenv/versions/3.14.10/bin/python3.14
command = /home/circleci/.pyenv/versions/3.14.10/bin/python3 -m venv /tmp/meas/carry/venv
stderr:
(empty)
```

### E01-carry-in-consumer

```text
[id-user-before-preparation] exit=0
stdout:
1001
stderr:
(empty)

[uname-before-preparation] exit=0
stdout:
x86_64
stderr:
(empty)

[os-release-before-preparation] exit=0
stdout:
PRETTY_NAME="Ubuntu 24.04.5 LTS"
NAME="Ubuntu"
VERSION_ID="24.04"
VERSION="24.04.5 LTS (Noble Numbat)"
VERSION_CODENAME=noble
ID=ubuntu
ID_LIKE=debian
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
UBUNTU_CODENAME=noble
LOGO=ubuntu-logo
stderr:
(empty)

[which-python-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/python
stderr:
(empty)

[which-python3-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/python3
stderr:
(empty)

[which-pip-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/pip
stderr:
(empty)

[which-pip3-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/shims/pip3
stderr:
(empty)

[which-git-before-preparation] exit=0
stdout:
/usr/bin/git
stderr:
(empty)

[which-ssh-before-preparation] exit=0
stdout:
/usr/bin/ssh
stderr:
(empty)

[which-yamllint-before-preparation] exit=1
stdout:
(empty)
stderr:
(empty)

[python3-version-before-preparation] exit=0
stdout:
Python 3.14.10 (main, Oct 26 2026, 22:11:46) [GCC 13.3.0]
stderr:
(empty)

[stdlib-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/versions/3.14.10/lib/python3.14
stderr:
(empty)

[venv-state-before-preparation] exit=0
stdout:
/home/circleci/.pyenv/versions/3.14.10 /home/circleci/.pyenv/versions/3.14.10 False
stderr:
(empty)

[pip-version-before-preparation] exit=0
stdout:
pip 26.2.2 from /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/site-packages/pip (python 3.14)
stderr:
(empty)

[marker-sysconfig-before-preparation] exit=2
stdout:
(empty)
stderr:
ls: cannot access '/home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED': No such file or directory

[marker-usrlib-before-preparation] exit=0
stdout:
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
stderr:
(empty)

[marker-head-before-preparation] exit=0
stdout:
[externally-managed]
Error=To install Python packages system-wide, try apt install
 python3-xyz, where xyz is the package you are trying to
 install.

 If you wish to install a non-Debian-packaged Python package,
 create a virtual environment using python3 -m venv path/to/venv.
 Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
 sure you have python3-full installed.

 If you wish to install a non-Debian packaged Python application,
 it may be easiest to use pipx install xyz, which will manage a
 virtual environment for you. Make sure you have pipx installed.

 See /usr/share/doc/python3.12/README.venv for more information.
stderr:
(empty)

[candidate-role] exit=0
stdout:
{"in_venv": false, "marker_present": false, "os_id": "ubuntu", "os_version": "24.04", "python_present": true, "python_version": "3.14", "role": "E01"}
stderr:
(empty)

[candidate-pip] exit=0
stdout:
pip 26.2.2 from /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/site-packages/pip (python 3.14)
stderr:
(empty)

[carried-cfg] exit=0
stdout:
home = /home/circleci/.pyenv/versions/3.14.10/bin
include-system-site-packages = false
version = 3.14.10
executable = /home/circleci/.pyenv/versions/3.14.10/bin/python3.14
command = /home/circleci/.pyenv/versions/3.14.10/bin/python3 -m venv /tmp/meas/carry/venv
stderr:
(empty)

[carried-version] exit=127
stdout:
(empty)
stderr:
/tmp/meas/obs.sh: line 22: /tmp/meas/carried/venv/bin/yamllint: cannot execute: required file not found

[carried-prefix] exit=0
stdout:
/tmp/meas/carried/venv /tmp/meas/carried/venv/bin/python
stderr:
(empty)

[carried-relocated] exit=127
stdout:
(empty)
stderr:
/bin/bash: line 1: /tmp/meas/relocated/bin/yamllint: cannot execute: required file not found
```

### carry-in console script の補助証拠

| 回収ファイル | 先頭行 | SHA-256 |
| --- | --- | --- |
| evidence/E01-carry-in-consumer/supporting/carried/venv/bin/yamllint | #!/tmp/meas/carry/venv/bin/python | 285bb87d9f5461028dc0af587c475e3e56a7cdd4cc4e432259836424838d697d |
| evidence/E01-carry-in-consumer/supporting/relocated/bin/yamllint | #!/tmp/meas/carry/venv/bin/python | 285bb87d9f5461028dc0af587c475e3e56a7cdd4cc4e432259836424838d697d |
| evidence/E01-carry-in-producer/supporting/carry/venv/bin/yamllint | #!/tmp/meas/carry/venv/bin/python | 285bb87d9f5461028dc0af587c475e3e56a7cdd4cc4e432259836424838d697d |
