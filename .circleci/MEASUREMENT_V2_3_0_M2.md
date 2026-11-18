# v2.3.0 M2 実測記録 — #5545

**2026-11-19 追記**　#176 の追加測定結果と完了条件 C1〜C7 の照合は [§18](#m2-176) にある。§1〜§17 と付録 A・B の件数・判定は #172 時点のもの。

対象: Redmine project 318 / #5545、親 #5542、`230_ロードマップ` Wiki version 1。
実測は 2026-11-18 JST。Claude（ID 11）が初稿を作成した。ChatGPT Work（ID 10）が CircleCI の公開証拠を回収・照合して ZIP にまとめ、人間（ID 3）が保存して Claude に提供した。
この版には ChatGPT Work の照合・訂正を反映した。#172 の観測結果を記録し、#5545 の総合判定は追加測定後に行う。
製品機能の採用、対応環境の保証、Phase 4/6 の検証、公開の成功を示す文書ではない。

表記: 「観測」は pipeline 172 の読み取り（観測名を `code` で示す）に直接ある事実。
「推定」は複数の観測と設定内容から導いたもので、それ自体の読み取りはない。「未確認」「判定不能」は §12 にまとめる。

## 1. 結果と判断範囲

承認された E01–E04 の候補条件と revision/hash のゲートが 4 job すべてで成立し、hold と 4 compute job が成功した。
438 件の読み取り（100 + 100 + 119 + 119）について、索引の終了コード・結合ログ・回収された stdout/stderr をバイト単位で照合し、不一致はなかった（§15）。
想定した拒否や不在を観測するコマンドの非 0 は、job の失敗とは区別する。

- 明示方式ではファイルに保存した導入先を次の run step が読み、絶対パスの yamllint 1.38.0 で表示・列挙・lint ができた。導入 step は PATH を変更せず、後続の名前解決は4候補で ABSENT だった。
  後続 step の子シェルで PATH の先頭を venvB に変えた場合も、絶対パスで選んだ版は 1.38.0 だった。
- BASH_ENV 方式（M2-02）: 追記した内容は後続の別 run step に届いた。同じ job で 2 回目に追記した環境（venvB）が、1 回目の環境（venvA）より先に解決された。
  引用符なしで書いた `$(...)` は命令として実行され、単一引用符付きは文字列のまま残った。
- BASH_ENV 追記後の PATH に同じ項目が重複した。後続の非対話 bash が起動時に内容を再評価したと推定する。
  この影響は M2-02 以降の読み取りにも及んでおり、一部の読み取りは意図した対象を測れていない（§6、§12）。
- 表示・lint・listing（M2-03）では、PATH 先頭にある 1.37.1 が版表示に使われた。両 venv を含まない PATH で裸の `yamllint --version` は 127 を返した。Orb 経由での不在時の挙動は未測定。
  `python -m yamllint` は venvA・venvB の各 Python で成立した。
- 配置（M2-04）: install が受け取る入力は版のみ、execute は対象・設定・出力先を受け取る。出力先の拒否 6 件はいずれも yamllint 起動前の終了コード 2 だった。
- 保存用 Python（M2-05）: python3 が PATH にないと保存有効時は起動前に 2 で拒否、保存無効時は 0。venv の python3 だけでも保存は成立した。
  E01/E02 では `-I` なしだと作業ディレクトリの `select.py` を読み込み、`-I` 付きでは読み込まなかった。
- 出力契約（M2-06）: 保存失敗と lint 結果の優先順位を直接観測した。lint 成功後の保存失敗は 2、lint エラー後の保存失敗は 1 で、どちらも結果ファイルと一時ファイルは残らなかった。

D03・D05・D07・D08 の最終判断は後続の判断工程（#5547）で行う。本書は方式を採用しない。

### #172 の位置付けと残る比較

1. **#172 は同じ承認の下での 2 回目の起動である。** #171 は hold 承認後に 4 job が開始し、承認パラメーターの形式チェックで停止した（§2、§3）。
   測定ケース（M2-00 以降）は #171 では動いていないが、環境同定（M-00）と、E03/E04 では失敗 step より前に置かれた apt 準備の step が動いている。
#171 と #172 の commit・設定 hash は同一で、各回に個別の hold がある。計画 §8.1 は計画改訂後の再実行に別承認を求めている。同一版の入力訂正による再起動の回数は明記されていない。本記録では #172 を入力訂正後の実測として採用し、両方の起動を残す。
2. **既存の BASH_ENV 内容が保たれるかは判定不能。** 全候補で、追記前に BASH_ENV のファイルが存在しなかった（§6）。
3. **BASH_ENV の影響で一部の実行対象を特定できなかった。** `base-module-launch` の直接観測は 1.37.1。使用 Python は venvB と推定する。
   M2-04・M2-06 でどの yamllint が動いたかを示す読み取りはない（§12）。
4. **基底環境の python3 で保存した読み取りはない。** D05 の「PATH 上の python3 を維持する案」は、PATH の先頭が venv の python3 である状態でしか観測していない（§9）。
5. **計画にあって読み取りがないケースがある。** 警告を隠す指定のみ（strict なし）、環境選択そのものの失敗、yamllint 不在時の Orb スクリプトの診断など（§12）。

C3 の実行対象と C5 の保存用 Python の比較が方式判断に必要なため、#5545 の C7 は未完了とする。追加測定では §12 の不足に対応するケースを選び、新しい設定 hash・commit と H9 計画を実行前に承認する。

## 2. 入力版・承認・実行順序

| 項目 | 固定値 |
| --- | --- |
| リポジトリ | circleci-orbs-mamono210/yamllint |
| 技術基準 commit | `2fc343180c9e13660889ac5643b75fbcabd513ea` |
| 当初承認計画 commit | `dedbccb25625f9b2baecfd78b688f674d9532277` |
| 当初承認の記録 commit | `9bfdc4431792cd9870fc02c02194e1158c6c39ed` |
| 実行に適用した計画 commit（main） | `b49d6dfdbd14feb98cfc19e52ed99a912f0f739b` |
| 計画ファイル | `.circleci/MEASUREMENT_PLAN_V2_3_0.md` |
| 計画ファイル SHA-256 | `1b8b2109460a459bde86268764f455defdf97616a10219a64df6b3fe546df578` |
| 記録作成時の main | `c22645388712e507a138d77127988192fb4f80e9`（計画ファイルは `b49d6df` とバイト同一。追加は M1 記録のみ） |
| #5544 の成果物 | `.circleci/MEASUREMENT_V2_3_0_M1.md`、commit `c226453`、SHA-256 `b2387bcd246f1c75ed7a0ed993575157d0a69201f14aa299598ee31bf32da350` |
| 実験 branch | `exp/230-m2` |
| 実験 commit | `ebd63fd1426dab201f5190b7e337e65eed09ca5a` |
| 実験 commit の親 | `dedbccb25625f9b2baecfd78b688f674d9532277` |
| 旧実験 commit（履歴のみ） | `10adeeee88ecbc868ba5b26ed72e950416349fe2` |
| 設定 SHA-256 | `4ac54e23315313794f32f0052bf5f0e00eac092231c4cbbfb604d66bfbce2375` |
| commit subject | `Recover temporary measurement configuration for #5545. Do not merge.` |
| pipeline | 172 / `b2e04234-1cde-41e7-98ca-44cbf3e4f996` |
| workflow | `measure-m2` / `446154d5-9b5c-4eca-ab0c-105e6cad9006` |
| workflow 結果 | succeeded |

計画版と実験 commit は別の対象であり、互いの SHA 一致を要求しない。
4 job すべての `revision-sha`、`config-hash`、`worktree-clean`、`revision-branch`、`commit-subject`、`pipeline` が上表と一致した。
ゲートは `CIRCLE_SHA1`・`CIRCLE_BRANCH` との一致も確認し、4 job とも成功の note（`approved revision and configuration matched; checkout is clean`）を残した。
CircleCI の処理済み設定では、#172 の4ジョブに展開された `MEAS_APPROVED_COMMIT` と `MEAS_APPROVED_CONFIG_SHA256` は上表の実験 SHA・設定 SHA-256 とそれぞれ完全一致した。#171 は4ジョブとも SHA の先頭にタブ（U+0009）が1文字付き、設定 hash は一致した。これはジョブに渡った値で、UI の入力操作は観測していない。

本書の作成時（2026-11-18）に GitHub から実験 commit を取得し、次を確認した。
branch `exp/230-m2` の先頭は `ebd63fd…`、親は `dedbccb…`、親との差分は `.circleci/config.yml` の 1 件、その SHA-256 は `4ac54e23…`。
#171 の失敗後から #172 の起動までに、ChatGPT Work は GitHub の承認対象の設定 hash を照合し、正しい入力値を会話で提示した。人間が各起動の前に行った remote 照合の独立記録は未取得。
Redmine #5544 journal 11293 は計画 `b49d6df` の main 反映、11297 は M1 成果物 `c226453`・SHA-256・完了を確認している。

### 時系列（すべて JST、UTC+09:00）

| 出来事 | JST | 根拠・精度 |
| --- | --- | --- |
| 当初の実測範囲承認 | 2026-11-15 21:41 | 計画 §11.1。受領時計 21:41:47。会話の正確な投稿時刻ではない |
| 実験 commit の作成 | 2026-11-17 20:59:06 | GitHub から取得した commit の author/committer date |
| 復旧後の実験 commit の承認 | 2026-11-17 21:21 | 計画 §11.1 / #5545 本文。受領時計 21:21:31 |
| 計画 `b49d6df` の commit | 2026-11-17 21:47:30 | main の commit date |
| M1 記録 `c226453` の commit | 2026-11-17 22:40:57 | main の commit date |
| #5544 の終了 | 2026-11-17 23:04:40 | Redmine #5544 `closed_on`（status 終了、進捗 100%） |
| push による pipeline #170 | 2026-11-18 20:58:27.164 | run `f05d68d8-d91b-49cb-8748-313fac7f9f00`、結果 not_run |
| #171 の作成 | 2026-11-18 21:03:45.142 | run `a7de7468-81fb-4fde-aced-d4505f44a8df` |
| #171 の hold 成功終了 | 2026-11-18 21:04:09.731 | CircleCI v2 workflow jobs の stopped_at |
| #171 の最初の compute job 開始 | 2026-11-18 21:04:12.624 | E03 の started_at |
| #171 の workflow 終了（failed） | 2026-11-18 21:04:54.918 | CircleCI v2 workflow の stopped_at |
| #172 の作成 | 2026-11-18 21:14:44.863 | run created_at。workflow created_at は 21:14:45.154 |
| #172 の hold 開始 | 2026-11-18 21:14:45.408 | workflow jobs API の started_at |
| #172 の hold 成功終了 | 2026-11-18 21:14:52.395 | v2 workflow jobs の stopped_at。独立した approved_at フィールドではない |
| #172 の最初の compute job 開始 | 2026-11-18 21:14:55.301 | E03 の started_at。step 単位の最早は E03 の spin-up 21:14:54.656（run.json） |
| #172 の全 job 終了 | 2026-11-18 21:16:09.291 | E04 / v2 workflow の stopped_at |
| 証拠 ZIP の受領 | 2026-11-18 22:15 | この記録作成の会話での受領時刻。ZIP 内に回収時刻の記録はない |

承認（11月15日 21:41、11月17日 21:21）→ #5544 終了 → push → hold 成功 → compute job 開始、の順を #171・#172 の両方で確認した。
最も早い compute job の開始は #171 の 21:04:12.624 で、これも復旧後の承認より後である。
計画は #171 と #172 の間で改訂されていない。実験 commit・設定 hash も同じである。
#171 の hold（job 2473）と #172 の hold（job 2478）の `approved_by` は同一の CircleCI アカウント ID だった。公開 API から実名・Redmine ID 3 との対応は確認できなかった。両回で compute job は各4件開始した。クレジット実消費は未取得。
確認元は [#171 の処理済み設定](https://circleci.com/api/v2/pipeline/a7de7468-81fb-4fde-aced-d4505f44a8df/config)、[#172 の処理済み設定](https://circleci.com/api/v2/pipeline/b2e04234-1cde-41e7-98ca-44cbf3e4f996/config)、[#171 の job 一覧](https://circleci.com/api/v2/workflow/7048c6e8-1659-4e6e-be80-39350c2520fd/job)、[#172 の job 一覧](https://circleci.com/api/v2/workflow/446154d5-9b5c-4eca-ab0c-105e6cad9006/job)。

計画 §11.2 が各 stage の実測記録に求める #5545 の実行値を以下に記す。

| 項目 | 値 |
| --- | --- |
| Plan version used | `b49d6dfdbd14feb98cfc19e52ed99a912f0f739b` |
| Experiment commit recorded by the job | `exp/230-m2`、`ebd63fd1426dab201f5190b7e337e65eed09ca5a` |
| Configuration hash recorded by the job | `4ac54e23315313794f32f0052bf5f0e00eac092231c4cbbfb604d66bfbce2375` |
| Hold approved at | 2026-11-18 21:14 JST（#172。停止した #171 は 21:04 JST） |
| Run start | 2026-11-18 21:14 JST（#172。停止した #171 は 21:04 JST） |
| Where recorded | `.circleci/MEASUREMENT_V2_3_0_M2.md` |

## 3. 実行一覧

### pipeline 172（今回の実測）

| job | 番号 | 結果 | 開始 JST | 終了 JST |
| --- | --- | --- | --- | --- |
| hold-until-approved | 2478（ID `d9b93ef7-0921-4bd2-9b5a-9eedf63abbe0`） | succeeded | 21:14:45.408 | 21:14:52.395 |
| m2-E01-cimg-py314 | [2481](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/172/workflows/446154d5-9b5c-4eca-ab0c-105e6cad9006/jobs/2481) | succeeded | 21:14:55.323 | 21:15:21.440 |
| m2-E02-cimg-py313 | [2479](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/172/workflows/446154d5-9b5c-4eca-ab0c-105e6cad9006/jobs/2479) | succeeded | 21:14:55.435 | 21:15:42.773 |
| m2-E03-ubuntu-2204 | [2480](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/172/workflows/446154d5-9b5c-4eca-ab0c-105e6cad9006/jobs/2480) | succeeded | 21:14:55.301 | 21:15:42.302 |
| m2-E04-ubuntu-2404 | [2482](https://app.circleci.com/pipelines/github/circleci-orbs-mamono210/yamllint/172/workflows/446154d5-9b5c-4eca-ab0c-105e6cad9006/jobs/2482) | succeeded | 21:14:55.639 | 21:16:09.291 |

[CircleCI workflow](https://app.circleci.com/workflow/446154d5-9b5c-4eca-ab0c-105e6cad9006)。
設定は Docker executor / `resource_class: small`、compute 4 件と executor を使わない approval 1 件で、実際の job 一覧もこの 5 件と一致する。
run.json では E01/E02 が 21 step、E03/E04 が 23 step で、すべての step が success（run step の exit code は 0）。クレジット実消費は取得していない。

測定の各ケースは別々の run step である。step 番号は次のとおり（E03/E04 は apt 準備と準備後の同定が入るため 2 つずれる）。

| ケースの step | E01/E02 | E03/E04 |
| --- | --- | --- |
| M2-00 二つの venv・fixture・runner | 106 | 108 |
| M2-01a / 01b / 01c | 107 / 108 / 109 | 109 / 110 / 111 |
| M2-02a / 02b / 02c / 02d | 110 / 111 / 112 / 113 | 112 / 113 / 114 / 115 |
| M2-03 / M2-04 / M2-05 / M2-06 / M2-07 | 114 / 115 / 116 / 117 / 118 | 116 / 117 / 118 / 119 / 120 |

### pipeline 171（承認パラメーターの形式チェックで停止した試行）

workflow `measure-m2` / `7048c6e8-1659-4e6e-be80-39350c2520fd`、結果 failed。実験 commit は #172 と同じ `ebd63fd…`。

| job | 結果 | 開始 JST | 終了 JST | 失敗 step |
| --- | --- | --- | --- | --- |
| hold-until-approved | succeeded | 21:03:45.613 | 21:04:09.731 | - |
| m2-E01-cimg-py314 | failed | 21:04:12.774 | 21:04:20.083 | 105 |
| m2-E02-cimg-py313 | failed | 21:04:12.650 | 21:04:35.258 | 105 |
| m2-E03-ubuntu-2204 | failed | 21:04:12.624 | 21:04:54.918 | 107 |
| m2-E04-ubuntu-2404 | failed | 21:04:12.656 | 21:04:36.259 | 107 |

4 job とも失敗 step は `Check the approved experiment revision`、終了コード 1、出力は `STOP: approved commit is missing or malformed`。
これはゲートの最初の検査（`approved-commit` が 40 桁の 16 進かどうか）であり、checkout の SHA や設定 hash との比較より前で止まっている。
#171 の処理済み設定では4ジョブとも承認済み SHA の直前に1文字のタブがあった。設定 hash は承認値に一致した。
各 job の step 結果で、ゲート前の helper 準備・M-00・候補検査・checkout の成功を確認した。E03/E04 では apt 準備と再同定も成功した。#171 の artifact は #172 の証拠 ZIP に含まれない。
M2-00 以降の測定ケースは #171 では実行されていない（ゲートの失敗で job が終了）。本書の観測値はすべて #172 のものである。

### push による pipeline #170

run `f05d68d8-d91b-49cb-8748-313fac7f9f00`、結果 not_run。パラメーター未指定の push では測定 workflow が選ばれない設計（計画 §8）と一致する。

## 4. 候補の再同定（M-00、M2-00）

下表はタグ名からの推定ではなく、#172 の job 内の観測値。E03/E04 は apt 準備後の値。

| 候補 | イメージ参照 | OS | UID | architecture | Python | python3 解決先 | python | 使用 stdlib 標識 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E01 | cimg/python:3.14 | Ubuntu 24.04 | 1001 | x86_64 | Python 3.14.10 | /home/circleci/.pyenv/shims/python3 | 有 | 無 |
| E02 | cimg/python:3.13 | Ubuntu 22.04 | 1001 | x86_64 | Python 3.13.18 | /home/circleci/.pyenv/shims/python3 | 有 | 無 |
| E03 | ubuntu:22.04 | Ubuntu 22.04 | 0 | x86_64 | Python 3.10.12 | /usr/bin/python3 | 無 | 無 |
| E04 | ubuntu:24.04 | Ubuntu 24.04 | 0 | x86_64 | Python 3.12.3 | /usr/bin/python3 | 無 | 有 |

観測名: `id-user-*`、`uname-*`、`os-release-*`、`python3-version-*`、`which-python*-*`、`stdlib-*`、`marker-sysconfig-*`、`marker-usrlib-*`、`venv-state-*`、`candidate-role`、`candidate-pip`。

#5544 の記録（`c226453` の §4）との対応: 上表の全項目が M1 の実測値と同じである。
E03/E04 の apt パッケージ版（git、python3、python3-pip、python3-venv）も M1 の記録と同じだった（`apt-versions`）。
E01 の `/usr/lib/python3.12/EXTERNALLY-MANAGED` は M1 と同じく存在したが、使用中の pyenv Python の標識ではない。
全候補で準備済みの基底 Python は仮想環境の外にあり、基底 PATH では `command -v yamllint` が1を返した。Python パッケージの有無はこの観測だけでは判定できない。

M1 との違い（設定上のもの）:

- E03/E04 の準備は 1 段で、`python3-venv` を最初から含む（`apt-install`）。M1 の stage A → 失敗 → stage B という分離は M2 では再現していない。
- M2 は基底環境へ yamllint を導入しない。そのため M1 の E01–E03 で見えた「基底導入先が PATH で解決される」状態は M2 にはない。
- 完全なイメージ digest は spin-up ログに出力されておらず、今回も取得できなかった。

M2-00 では全候補で二つの venv を作り、別々の版を導入した（`venv-a-create`、`venv-a-install`、`venv-b-create`、`venv-b-install` はすべて 0）。

| venv | 場所 | yamllint | 依存 |
| --- | --- | --- | --- |
| venvA | /tmp/meas/venvA | 1.38.0 | pathspec 1.1.1、PyYAML 6.0.3 |
| venvB | /tmp/meas/venvB | 1.37.1 | pathspec 1.1.1、PyYAML 6.0.3 |

fixture は `/tmp/meas/fixtures` で、`.yamllint`（実験 checkout からのコピー）、`custom.yml`、`tree/ok.yml`・`tree/warn.yml`・`tree/broken.yml`、`warn.cfg`、`warnmany/` 40 件、`errmany/` 40 件。
`/tmp/meas/slim` は bash と venvA の yamllint へのシンボリックリンクだけを置いたディレクトリで、python3 のない PATH を作るために使う（`slim-bin`）。

## 5. 明示方式の引き継ぎ（M2-01）

step A（M2-01a）が導入先を `/tmp/meas/venv_path` に書き、別の run step（M2-01b）がそれを読んで絶対パスで実行した。step A から step B へ export したものはない。

| 観測名 | E01 | E02 | E03 | E04 | 観測内容 |
| --- | --- | --- | --- | --- | --- |
| `producer-same-step` | 0 | 0 | 0 | 0 | 導入 step 内: yamllint 1.38.0 |
| `consumer-inherited` | 0 | 0 | 0 | 0 | 別 step で `command -v yamllint`: ABSENT（0 は ABSENT を出力した結果） |
| `consumer-explicit-version` | 0 | 0 | 0 | 0 | 絶対パスの `--version`: yamllint 1.38.0 |
| `consumer-explicit-listing` | 0 | 0 | 0 | 0 | 絶対パスの `--list-files .`: 85 件 |
| `consumer-explicit-lint` | 0 | 0 | 0 | 0 | 絶対パスで `tree/ok.yml` を lint: 出力なし |
| `after-consumer-path-change-resolved` | 0 | 0 | 0 | 0 | PATH 先頭に venvB を置くと名前解決は venvB の 1.37.1 |
| `after-consumer-path-change-explicit` | 0 | 0 | 0 | 0 | 同じ PATH でも絶対パス指定は 1.38.0 |

- `producer-path` と `consumer-path` は候補ごとに同じ値で、導入 step は PATH を変えていない。
- 列挙の 85 件は `.yamllint`、`custom.yml`、`tree/` 3 件、`errmany/` 40 件、`warnmany/` 40 件。4 候補で集合は同じ。並び順は E01/E02 と E03/E04 で異なる（sort の照合順序の違いと推定）。
- M2-01c の PATH 変更は、別 run step の中で、読み取りコマンドの内側に `export PATH=…` を書いたものである。step をまたいで残る PATH 変更ではない。
- 明示方式で lint したのは `tree/ok.yml` だけで、計画の「fixture tree の lint」のうち警告・エラーを含むファイルは、この方式では lint していない。

## 6. BASH_ENV 方式の引き継ぎ（M2-02）

BASH_ENV の中身は一度も出力していない。大きさと hash の先頭 12 桁だけを記録した。

| 観測名 | E01 | E02 | E03 | E04 | 観測内容 |
| --- | --- | --- | --- | --- | --- |
| `bash-env-name` | 0 | 0 | 0 | 0 | 変数は設定済み（`/tmp/.bash_env-<job ID>-0-build`） |
| `bash-env-remember` | 0 | 0 | 0 | 0 | `BASH_ENV file absent`: 追記前にファイルは存在しない |
| `bash-env-after-append` | 0 | 0 | 0 | 0 | 1 回目の追記後: 64 バイト、2 行、`9705a53921fd` |
| `bash-env-later-path` | 0 | 0 | 0 | 0 | 別 step の PATH 先頭: `/tmp/meas/venvA/bin` が 2 回 |
| `bash-env-later-resolve` | 0 | 0 | 0 | 0 | 別 step の名前解決: /tmp/meas/venvA/bin/yamllint、1.38.0 |
| `bash-env-marker-kept` | 0 | 0 | 0 | 0 | 別 step で `MEAS_MARKER_KEPT=1` |
| `bash-env-prefix-unchanged` | 0 | 0 | 0 | 0 | `no pre-existing content to compare; current bytes=64` |
| `bash-env-second-append` | 0 | 0 | 0 | 0 | 2 回目の追記後: 205 バイト、5 行、`439d962c0dc9` |
| `value-unquoted` | 0 | 0 | 0 | 0 | `MEAS_VALUE=/tmp/meas/AINJECTEDB`（`$(echo INJECTED)` が実行された） |
| `value-quoted` | 0 | 0 | 0 | 0 | `MEAS_VALUE_QUOTED=/tmp/meas/A$(echo INJECTED)B`（文字列のまま） |
| `path-after-two-appends` | 0 | 0 | 0 | 0 | PATH 先頭: venvB、venvA、venvB、venvA の順 |
| `resolve-after-two-appends` | 0 | 0 | 0 | 0 | 名前解決: /tmp/meas/venvB/bin/yamllint、1.37.1 |

観測から言えること:

- **別 step への到達**: 追記した 2 行（目印の変数と PATH）は、別 run step で有効だった。明示方式と違い、後続 step は何も指定せずに venvA を解決した。
- **順次利用**: 2 回目に venvB を追記すると、以後は venvB が先に解決された。venvA の項目は PATH に残っている。後から追記したものが優先される。
- **値の命令化**: 引用符なしの値に含まれる `$(…)` は、後続 step で命令として実行された。単一引用符で囲んだ値は実行されなかった。
- **再評価**: PATH に同じ項目が 2 回ずつ現れた。読み取りは step のシェルから起動した子の bash で行っており、step のシェルと子の bash の両方が BASH_ENV を評価したと推定する。
  step のシェル自身の PATH を直接記録した読み取りはない。

追記した文字列から計算した大きさと hash は、観測値と一致した（記録作成時の計算。64 バイト・2 行・`9705a53921fd`、205 バイト・5 行・`439d962c0dc9`）。
つまり、ファイルの内容は設定が追記した 5 行だけで、1 回目の 2 行は 2 回目の追記後もそのまま残っていたと推定する。

判定不能・注意:

- **既存内容の保全は判定不能**。全候補で追記前のファイルがなく、「利用者が先に書いた内容が壊れないか」を比べる対象がなかった。
- **初回追記前の不在**は、計画 M2-02 の指示に沿って記録した。その後の初回追記でファイルが作成され、後続への到達を観測した。利用者があらかじめ持っていた内容の保全は別条件として残る。
- **後続ケースへの影響**。BASH_ENV のファイルは job の終わりまで残る。M2-03 以降で起動される bash（`obs_sh` の子 bash、`run_exec.sh`、その先の `execute.sh`）は、
  起動のたびに PATH の先頭へ venvB、venvA を付け直すと推定する。M2-05 だけは `env -u BASH_ENV` でこれを外している。影響を受けた読み取りは §12 に挙げる。

## 7. 表示・lint・listing の実行対象（M2-03）

| 観測名 | E01 | E02 | E03 | E04 | 観測内容 |
| --- | --- | --- | --- | --- | --- |
| `show-version-script` | 0 | 0 | 0 | 0 | 基準版 show-version.sh: `yamllint 1.37.1`、`resolved=/tmp/meas/venvB/bin/yamllint` |
| `execute-script-listing` | 0 | 0 | 0 | 0 | 基準版 execute.sh の列挙: 85 件（M2-01 の列挙と同じ集合） |
| `execute-script-lint` | 0 | 0 | 0 | 0 | 基準版 execute.sh で `tree/ok.yml` を lint: 出力なし |
| `selected-a-module-file` | 0 | 0 | 0 | 0 | venvA の Python: `…/venvA/lib/pythonX.Y/site-packages/yamllint/__init__.py 1.38.0` |
| `selected-a-module-launch` | 0 | 0 | 0 | 0 | venvA の Python で `-m yamllint --version`: 1.38.0 |
| `selected-b-module-launch` | 0 | 0 | 0 | 0 | venvB の Python で `-m yamllint --version`: 1.37.1 |
| `destination-not-on-path` | 127 | 127 | 127 | 127 | PATH を `/usr/bin:/bin` にすると `resolved=ABSENT`、`yamllint: command not found` |
| `base-module-launch` | 0 | 0 | 0 | 0 | `python3 -m yamllint --version`: 1.37.1（実行 Python は未同定。下記） |

- **PATH に別版がある場合**: PATH を venvB、venvA の順にすると、版表示は先頭の venvB（1.37.1）を解決した。venvA（1.38.0）を選んだつもりでも、表示は PATH の順で決まる。
- **導入先が PATH にない場合**は裸の `yamllint --version` が 127 を返した。Orb 経由の不在時診断と暗黙代替の判定は追加測定に残る。
- **モジュール起動**は絶対パスで指定した venvA と venvB の両 Python で成立した。`yamllint.__file__` を直接記録したのは venvA。venvB では版を記録した。
- **表示と検査が同じ導入物か**: 表示・列挙・lint の 3 件は同じ PATH 指定で実行したが、解決先を記録したのは表示だけである。
  列挙と lint を実行した yamllint の版・場所を示す読み取りはない（execute.sh は版を出力しない）。同じ導入物だったことは PATH の順序からの推定にとどまる。
- **基底環境でのモジュール起動は未確認。** `base-module-launch` の出力は 1.37.1 で、BASH_ENV により子シェルの PATH 先頭に来た venvB が使われたと推定する。実行した `sys.executable` は採取していない。

## 8. 配置制約を判定できる command（M2-04）

基準版の入力（実験 checkout 内の `src/commands/*.yml` を grep した結果）:

- `install-inputs`: install が受け取るのは `PARAM_VERSION` の 1 項目（install.yml 17 行目）。検査対象・設定・出力先は受け取らない。
- `execute-inputs`: execute は 8 項目を受け取る（execute.yml 79〜86 行目）。
  `PARAM_TARGETS`、`PARAM_CONFIG_FILE`、`PARAM_CONFIG_DATA`、`PARAM_STRICT`、`PARAM_NO_WARNINGS`、`PARAM_LIST_FILES`、`PARAM_FORMAT`、`PARAM_OUTPUT_FILE`。
- どちらの入力にも、導入先（venv の場所）を表す項目はない。

出力先を変えて基準版 execute.sh を実行した結果（4 候補で同一）:

| 観測名 | E01 | E02 | E03 | E04 | 診断（stderr）または結果 |
| --- | --- | --- | --- | --- | --- |
| `out-inside-target-dir` | 2 | 2 | 2 | 2 | `'tree/report.txt' is inside the target directory 'tree'; save it outside every target directory; yamllint was not run` |
| `out-equal-target-file` | 2 | 2 | 2 | 2 | `'tree/ok.yml' already exists as a regular file; existing entries are never replaced; yamllint was not run` |
| `out-equal-config-file` | 2 | 2 | 2 | 2 | `'custom.yml' already exists as a regular file; existing entries are never replaced; yamllint was not run` |
| `out-parent-missing` | 2 | 2 | 2 | 2 | `the parent directory '/tmp/meas/absent' does not exist and is not created; yamllint was not run` |
| `out-already-exists` | 2 | 2 | 2 | 2 | `'/tmp/meas/fixtures/custom.yml' already exists as a regular file; existing entries are never replaced; yamllint was not run` |
| `out-parent-not-a-directory` | 2 | 2 | 2 | 2 | `the parent 'custom.yml' is not a directory; yamllint was not run` |
| `out-dotdot` | 1 | 1 | 1 | 1 | 拒否されない。`tree` を lint し、結果 187 バイトを `/tmp/meas/out/dotdot.txt` に保存。1 は lint の終了コード |
| `out-outside-targets` | 0 | 0 | 0 | 0 | 拒否されない。`/tmp/meas/out/report-ok.txt` を 0 バイトで作成 |

診断の先頭はすべて `yamllint Orb: output_file: rejected: `。拒否の 6 件は stdout が空で、yamllint は起動していない（診断の文言による）。

- **機械的に拒否できる範囲**: execute は対象・設定・出力先を同時に知っているので、出力先と対象ディレクトリの包含、既存の有無、親の有無と種類を起動前に判定している。
- **install が判定できないこと**: install は対象を受け取らない。導入時に「導入先が検査対象の内側か」を判定する情報は、基準版の入力にはない。
- **導入先と対象の関係**: #5544 は、venv を検査対象の内側に作ると列挙対象が増えることを観測した。
  基準版の execute には導入先を表す入力がないので、execute が導入先と対象の包含を判定するには新しい情報の受け渡しが要る。これは観測から導いた整理で、方式の提案ではない。
- **対象と同じ・設定と同じ出力先は判定不能**: `out-equal-target-file` と `out-equal-config-file` の診断は「既に存在する」だった。
  既存のファイルと同じパスは必ず既存の検査に先にかかるため、「対象と同じ」「設定ファイルと同じ」という専用の拒否は、このケースでは観測できていない。
- **`..` を含むパス**: `/tmp/meas/out/../out/dotdot.txt` は拒否されず、解決後の場所に保存された。`..` という表記そのものは拒否理由になっていない。
- M2-04 で動いた yamllint の版は記録されていない（§12）。拒否の 6 件は yamllint の起動前なので、この不明は影響しない。

## 9. 保存に使う Python（M2-05）

M2-05 の保存呼び出しはすべて `env -u BASH_ENV` で BASH_ENV を外し、PATH を明示している。

`helper-contract`（基準版 execute.sh の該当行）: 保存補助処理は `python3 -I` で動き、import は `os`、`select`、`stat`、`sys` の 4 つ（88〜91 行目）。
`command -v python3` の検査（322 行目）の後、`python3 -I -c` を 3 か所（328、338、343 行目）で呼ぶ。

| 観測名 | E01 | E02 | E03 | E04 | PATH の条件と結果 |
| --- | --- | --- | --- | --- | --- |
| `save-with-path-python3` | 0 | 0 | 0 | 0 | 先頭が venvA/bin、以降は step の PATH。`base.txt` を作成 |
| `save-without-python3` | 2 | 2 | 2 | 2 | `/tmp/meas/slim` のみ。`could not prepare the output: python3 was not found on PATH; yamllint was not run` |
| `save-with-only-venv-python3` | 0 | 0 | 0 | 0 | venvA/bin と slim のみ。`venvpy.txt` を作成 |
| `save-disabled-without-python3` | 0 | 0 | 0 | 0 | slim のみ・保存無効。python3 がなくても成功 |
| `venv-helper-modules` | 0 | 0 | 0 | 0 | venvA の Python を `-I` で起動し 4 モジュールを import: `modules ok` |
| `save-with-local-select` | 0 | 0 | 0 | 0 | 作業ディレクトリに `select.py` を置いて保存。`isolated.txt` を作成 |
| `isolation-without-I` | 1 | 1 | 0 | 0 | E01/E02: `LOCAL select.py WAS IMPORTED`。E03/E04: `<built-in>` |
| `isolation-with-I` | 0 | 0 | 0 | 0 | E01/E02: 標準ライブラリの `lib-dynload/select.cpython-*.so`。E03/E04: `<built-in>` |

`saved-files` では `base.txt`、`venvpy.txt`、`isolated.txt` が 0 バイトで存在し、拒否された `nopy.txt` は存在しない。対象は警告もエラーもない `tree/ok.yml` なので、保存内容は空である。

- **保存無効時の依存**: python3 のない PATH でも保存無効なら成功した。保存無効の既存経路に保存用の依存は加わっていない。
- **不足時の診断**: 保存有効で python3 がないと、yamllint の起動前に 2 で拒否し、結果ファイルを作らなかった。
- **選択環境の Python を使う案**: PATH 上の python3 が venvA のものだけでも保存は成立した。venvA の Python で必要な 4 モジュールは `-I` 付きで import できた。
- **分離（E01/E02）**: `-I` なしでは作業ディレクトリの `select.py` が読み込まれ、`-I` 付きでは標準ライブラリ側が読み込まれた。
  その状態で保存（`save-with-local-select`）は成功しており、`python3 -I` の分離が venv の Python でも働いたことを示す。
- **分離（E03/E04）は判定不能**: `select` が組み込みモジュールで、`-I` の有無にかかわらず `<built-in>` だった。
  作業ディレクトリの `select.py` では分離の有無を区別できない（計画 M2-05 が予告していた限界）。保存が成功したことは、分離が働いた証拠にならない。
- **基底環境の python3 での保存は未観測**: 「基準」の読み取り `save-with-path-python3` も PATH の先頭は venvA/bin である。
  `save-with-only-venv-python3` が示すとおり venvA/bin には python3 があるので、この読み取りが使ったのも venvA の python3 だったと推定する。
  M2-06 の保存も同様に venv の python3 を使ったと推定する（§12）。保存時に解決された python3 の場所を記録した読み取りはない。
- 上の点から、D05 の 2 案について言えるのは次の範囲である。venv の bin を PATH の先頭に置く引き継ぎ方では、「PATH 上の python3」は venv の python3 になり、2 案は同じ対象を指す。
  2 案が別の対象になる条件（PATH を変えずに絶対パスで yamllint を起動する場合の基底 python3）での保存は、この実測にない。

## 10. 出力契約と終了コードの優先順位（M2-06）

### 第 1 部: 保存の有無と出力

| 観測名 | E01 | E02 | E03 | E04 | 条件 | stdout | 保存ファイル |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `clean-save-disabled` | 0 | 0 | 0 | 0 | 問題なし・保存無効 | 空 | なし |
| `clean-save-enabled` | 0 | 0 | 0 | 0 | 問題なし・保存有効 | 空 | `clean.txt` 0 バイト |
| `lint-error-save-enabled` | 1 | 1 | 1 | 1 | 構文エラー・保存有効 | エラー 113 バイト | `error.txt` 113 バイト |
| `warning-only-not-strict` | 0 | 0 | 0 | 0 | 警告のみ | 警告 74 バイト | `warn.txt` 74 バイト |
| `warning-only-strict` | 2 | 2 | 2 | 2 | 警告のみ・strict | 警告 74 バイト | `strict.txt` 74 バイト |
| `warning-only-strict-no-warnings` | 2 | 2 | 2 | 2 | 警告のみ・strict・警告非表示 | 空 | `strictnw.txt` 0 バイト |
| `collision-refused` | 2 | 2 | 2 | 2 | 既存の `clean.txt` を指定 | 空 | 既存ファイルは 0 バイトのまま |
| `unwritable-parent` | 2 | 2 | 0 | 0 | 親が書き込み不可（権限 500） | 空 | E01/E02: 起動前に拒否 |

- 保存有効でも lint 結果は stdout に出た。内容のある保存ファイル 6 種（`dotdot`、`error`、`warn`、`strict`、`warnmany`、`errmany`）は、
  対応する読み取りの stdout とバイト単位で一致した（4 候補とも。記録作成時に ZIP 内のファイルで照合）。
- Orb の診断は stderr に出た。拒否のときの stdout は空だった。lint の結果は stderr に出ていない。
- `collision-refused` の診断: `'/tmp/meas/out/clean.txt' already exists as a regular file; existing entries are never replaced; yamllint was not run`。
- `unwritable-parent` は `current-uid` と組で読む。E01/E02（UID 1001）は
  `could not prepare the output: cannot create a temporary file in '/tmp/meas/ro': Permission denied; yamllint was not run` で 2。
  E03/E04（UID 0）は権限ビットでは止まらず 0 だった。計画どおり、root の候補にはこのケースを適用しない。
- 版表示は M2-06 では実行していない。execute.sh を通した読み取り（候補あたり 27 件）の stdout・stderr に版の文字列はなかった。
  版表示は別スクリプト（show-version.sh）の出力で、観測は §7 の `show-version-script` の 1 件である。

### 第 2 部: lint 結果と保存失敗の優先順位

`run_limited.sh` は Orb のスクリプトだけにファイルサイズ上限（`ulimit -f 1`）をかけ、stdout・stderr は上限のない読み手を通して全量を残す。

| 観測名 | E01 | E02 | E03 | E04 | 条件 | stdout | stderr |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `control-lint-ok-many-warnings` | 0 | 0 | 0 | 0 | 警告 40 件・上限なし | 3,591 バイト | 空 |
| `control-lint-error-many` | 1 | 1 | 1 | 1 | エラー 40 件・上限なし | 4,511 バイト | 空 |
| `save-fails-after-lint-ok` | 2 | 2 | 2 | 2 | 警告 40 件・上限あり | 3,591 バイト（対照と同一） | 保存失敗の診断、`orb_exit=2` |
| `save-fails-after-lint-error` | 1 | 1 | 1 | 1 | エラー 40 件・上限あり | 4,511 バイト（対照と同一） | 保存失敗の診断、`orb_exit=1` |
| `limited-results-absent` | 2 | 2 | 2 | 2 | 上限ありの 2 件の結果ファイル | どちらも存在しない（2 は ls の終了コード） | - |
| `temporary-files-left` | 0 | 0 | 0 | 0 | 一時ファイルの残存 | `no temporary file left behind` | - |

保存失敗の診断（2 件とも同じ形。一時ファイル名の乱数部分だけが異なる）:

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-<16 桁>.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-ok.txt' was not created
```

- lint が成功（警告のみ）で保存が失敗すると 2。lint がエラーで保存も失敗すると 1。yamllint の非 0 が保存失敗より優先される、という基準版の順位を直接観測した。
- どちらの場合も stdout の lint 結果は対照と同じ全量が出ており、結果ファイルも一時ファイルも残らなかった。
- 終了コードは `run_limited.sh` が記録した `orb_exit` と読み取りの終了コードが一致している。途中で 0 に変換した値ではない。
  読み手の終了コードも 0（`stdout_reader_exit=0 stderr_reader_exit=0`）だった。
- lint エラー後の保存失敗では、終了コード 1 だけからは保存失敗が分からない。保存失敗は stderr の診断でのみ分かる。

注意: M2-06 は step の先頭で PATH に venvA を足しているが、BASH_ENV が残っているため、実際に動いた yamllint は venvB（1.37.1）だったと推定する（§12）。
上の結果は基準版 execute.sh の出力の扱いと終了コードに関するもので、4 候補で同一だった。yamllint の版による違いがないことは、この実測では確かめていない。

## 11. 失敗コードと診断の一覧（M2-07）

M2-01〜M2-06 の非 0 を原因別に並べる。4 候補で同じ値のものは 1 行にまとめた。

| 区分 | 観測名 | 終了コード | 診断の出どころ・先頭 |
| --- | --- | --- | --- |
| 環境の解決 | `destination-not-on-path` | 127 | シェル。`yamllint: command not found`。Orb の診断ではない |
| 起動前拒否（出力先） | `out-inside-target-dir`、`out-equal-target-file`、`out-equal-config-file`、`out-parent-missing`、`out-already-exists`、`out-parent-not-a-directory`、`collision-refused` | 2 | Orb、stderr。`yamllint Orb: output_file: rejected: …; yamllint was not run` |
| 起動前拒否（保存の準備） | `save-without-python3` | 2 | Orb、stderr。`could not prepare the output: python3 was not found on PATH; yamllint was not run` |
| 起動前拒否（保存の準備） | `unwritable-parent`（E01/E02 のみ） | 2 | Orb、stderr。`could not prepare the output: cannot create a temporary file in …: Permission denied; yamllint was not run` |
| lint | `lint-error-save-enabled`、`out-dotdot`、`control-lint-error-many` | 1 | yamllint、stdout。`error  syntax error: …` |
| lint（strict の警告） | `warning-only-strict`、`warning-only-strict-no-warnings` | 2 | yamllint。stdout に警告（非表示指定なら空）。stderr は空 |
| 保存失敗（lint 成功後） | `save-fails-after-lint-ok` | 2 | Orb、stderr。`could not write the yamllint stdout to …: File too large` |
| 保存失敗（lint エラー後） | `save-fails-after-lint-error` | 1 | 終了コードは yamllint のもの。Orb の保存失敗は stderr のみ |
| 観測用コマンド | `isolation-without-I`（E01/E02）、`limited-results-absent` | 1、2 | Orb でも yamllint でもない。観測用の python・ls の終了コード |

終了コードだけでは区別できない組:

- **2**: 出力先の拒否、保存準備の失敗、lint 成功後の保存失敗、strict での警告。前の 3 つは stderr に Orb の診断があり、strict の警告は stderr が空である。
  `warning-only-strict-no-warnings` は stdout も stderr も空で 2 になる。
- **1**: lint エラーのみの場合と、lint エラーに保存失敗が重なった場合。後者は stderr の診断でしか区別できない。
- **起動前か起動後か**: 起動前拒否の診断は `yamllint was not run` で終わる。保存失敗（起動後）の診断にはこの語句がない。

D07・D08 に渡す観測限界:

- 環境選択そのものの失敗（存在しない導入先の指定、壊れた venv など）を Orb のスクリプトに与えた読み取りはない。127 は裸のコマンドの結果である。
- yamllint が見つからない状態で基準版 execute.sh・show-version.sh を実行した読み取りはない。そのときの終了コードと診断は未確認。
- 既存の入力拒否（対象・設定に関するもの）と新しい失敗の関係は、出力先の拒否 7 件の範囲でしか観測していない。
- `main-not-touched` は 4 候補とも出力なしの 0。測定後の実験 checkout に変更がなかったことを示す（main の照合は §14）。

## 12. 未確認・判定不能・未実行

| 対象 | 状態・理由 | 判断への制限 | 関係する完了条件 |
| --- | --- | --- | --- |
| 既存の BASH_ENV 内容の保全 | 判定不能。全候補で追記前のファイルがない | 追記が利用者の既存内容を壊さないことは示せない | C2 |
| step のシェル自身の PATH（BASH_ENV 方式） | 未取得。読み取りは子の bash | 再評価の回数は PATH の重複からの推定 | C2 |
| `base-module-launch` | 意図と異なる対象。venvB の python3 を解決したと推定 | 基底環境でのモジュール起動の可否は未確認 | C3 |
| 列挙・lint を実行した yamllint（M2-03） | 未取得。解決先の記録は版表示だけ | 表示と検査が同じ導入物かは PATH 順からの推定 | C3 |
| M2-04・M2-06 で動いた yamllint | 未取得。BASH_ENV の残存により venvB（1.37.1）と推定。step の意図は venvA | 出力契約の結果を「選択した環境での結果」とは言い切れない | C4、C6 |
| 保存時に解決された python3 の場所 | 未取得 | 基底 python3 での保存は未観測。D05 の 2 案が別対象になる条件の比較がない | C5 |
| E03/E04 の `-I` による分離 | 判定不能。`select` が組み込み | E03/E04 では分離の有無を区別できていない | C5 |
| 対象と同じ・設定と同じ出力先の専用拒否 | 判定不能。既存の検査が先にかかる | この 2 つの拒否理由は観測できていない | C4 |
| 警告非表示のみ（strict なし） | 未実行。設定にケースがない | 計画 M2-06 第 1 部の 1 条件が欠ける | C6 |
| 明示方式での警告・エラーを含む lint | 未実行。lint は `tree/ok.yml` のみ | 明示方式の lint は成功例だけ | C2 |
| 環境選択の失敗・yamllint 不在時の Orb の診断 | 未実行 | D07・D08 へ渡すコードと診断がこの範囲で欠ける | C6、C7 |
| root 候補の書き込み不可の親 | 適用外（計画どおり）。E03/E04 は 0 | 作成されたファイルの有無は記録していない | C6 |
| pipeline 入力の出所 | 4 job に展開された値を確認済み（§2）。UI の入力操作は未観測 | #171 は SHA に先頭タブ、#172 は承認した2値に一致 | C1 |
| push 後・起動前の remote 照合 | #171 後、#172 前の ChatGPT Work の照合を確認。各起動前の人間自身の記録は未取得 | 人間の操作時刻は推定しない | C1 |
| hold の承認者 | 両 hold の CircleCI ユーザー ID は同一。実名との対応は未確認 | Redmine ID 3 への対応は確定できない | C1 |
| #171 の実行範囲 | ゲート直前までの各 step 成功を確認。artifact は未回収 | #171 の測定ケースは計上しない | C1 |
| イメージ digest | spin-up ログに完全な digest なし | タグと観測実体は対応するが、バイト同一性は固定できない | C1 |
| E05 Debian 12 | 未実行。E04 が候補条件を満たした | Debian 12 の実測結果は本書にない | - |
| クレジット実消費・リモート branch 削除 | 未取得・未実施 | クリーンアップ済みとはしない | C7 |

## 13. D03・D05・D07・D08 と配置制約への対応

| 論点 | 判断材料（観測名） | この実測で確定しないこと |
| --- | --- | --- |
| D03 引き継ぎ方式 | ファイルに書いた導入先を次の step から使えた。子シェルで PATH を変えても明示した絶対パスは同じ版。BASH_ENV への追記は次の step に届き、後の追記が優先された（§5・§6） | 既存の利用者内容の保全、独立した利用者 step の後の経路、方式の採用 |
| D05 実行対象と暗黙代替 | 版表示は PATH 先頭を解決。両 venv の Python でモジュール起動可。両 venv のない PATH で裸のコマンドは127（§7） | 基底 Python の起動可否。実際に lint・列挙した導入物。Orb 経由の不在時診断。D03 の引き継ぎ先との対応 |
| D05: 保存用 Python | python3 不在時の拒否と診断、保存無効時は依存なし、venv の python3 だけで保存可、必要 4 モジュールあり、E01/E02 での `-I` の分離（`save-*`、`venv-helper-modules`、`isolation-*`、`helper-contract`） | 基底 python3 を使う場合との比較。E03/E04 での分離の確認。案の採用 |
| D07 エラーと観測 | §11 にコードと診断を対応付けた。複数原因が同じコードを返す。保存失敗との優先順位は §10 | 環境選択の失敗、yamllint 不在時の Orb の診断、既存入力拒否との順序 |
| D08 公開後の利用側での直接確認 | D03 の別 step と D05 の実行対象・保存 Python が公開後の確認候補。意図した失敗のプロセス終了値と CircleCI の実 step は区別して観測する | 必須経路・代表環境・意図した失敗 job 数・確認方法は #5547 で決定 |
| 配置制約 | install の入力は版のみ、execute は対象・設定・出力先を持つ。出力先の拒否は起動前に機械的に行われる。導入先を表す入力はどちらにもない（`install-inputs`、`execute-inputs`、`out-*`） | 導入先と対象の関係を誰が判定するかの決定。文書上の制約にとどめる範囲 |
| 出力契約 | 保存有効・無効、stdout と stderr の分離、新規ファイルのみ、衝突拒否、優先順位（§10） | 環境選択を加えた製品実装での保証。yamllint の版による差がないこと |

#5544 から引き継いだ事実との関係: M1 は「完成した venv は PATH に入らない」「venv を対象の内側に置くと列挙が増える」を観測した。
M2 は、その venv を別 step から使う 2 つの方法と、そのときの表示・検査・保存の参照先を観測した。M1 のコンテナや導入物は引き継いでおらず、M2 の job で再同定・再導入している。

## 14. 実行範囲と main の照合

測定設定（`exp/230-m2` の `.circleci/config.yml`、638 行）は setup 設定ではなく、workflow は `measure-m2` の 1 つ、`resource_class` は `small` のみ。
`context`・`publish` の語は設定に現れない。実行されたのは hold と compute 4 件である。

記録作成時（2026-11-18）に GitHub から取得した実体での照合:

```text
main = c22645388712e507a138d77127988192fb4f80e9
baseline = 2fc343180c9e13660889ac5643b75fbcabd513ea

git diff --name-status baseline main
A	.circleci/MEASUREMENT_PLAN_V2_3_0.md
A	.circleci/MEASUREMENT_V2_3_0_M1.md

git diff --name-status experiment^ experiment
M	.circleci/config.yml
```

| ファイルの版 | SHA-256 |
| --- | --- |
| baseline .circleci/config.yml | bbaca8dce8cae7118dcc720aa49475ca8cb3bf9f507b6f7d23f0ad4aad80941a |
| main .circleci/config.yml | bbaca8dce8cae7118dcc720aa49475ca8cb3bf9f507b6f7d23f0ad4aad80941a |
| exp/230-m2 .circleci/config.yml | 4ac54e23315313794f32f0052bf5f0e00eac092231c4cbbfb604d66bfbce2375 |

main の config と baseline の config はバイト単位で同一。`git log main -- .circleci/config.yml` の最新は次のとおりで、M1 記録の時点から変わっていない。

```text
9bdc52b627986e18a6da4ba02c8a621387f554e1 Phase 5 回帰と互換性の検証を公開条件に組み込んだ refs #5492
```

したがって、確認した main に測定設定は混入していない。本書の納品物は本書 1 ファイルで、実験 branch や実験設定を main に入れるものではない。
`main-not-touched`（4 候補とも出力なし）は実験 checkout の状態であり、リモート main の検証はこの節の照合による。
記録作成時点で、GitHub の branch は `main` と `exp/230-m2` の 2 つだった。`exp/230-m2` は削除されていない。

## 15. 証拠の保存と照合方法

ChatGPT Work が CircleCI の公開証拠を回収・照合して ZIP を作成し、人間が保存して Claude に提供した。M2 計画上の回収担当は人間であり、ここには実際の作業を記録する。

| 項目 | 値 |
| --- | --- |
| ファイル | `yamllint-5545-pipeline-172.zip`（191,436 バイト。受領時のファイル名は末尾に `_1` が付いていた） |
| SHA-256 | `5cf50553cec44e0c51f8bbe60d0c4adf94222651205804a648b0e552749664ae` |
| 内容 | 416 ファイル。`run.json`、`SHA256SUMS`、候補ごとの `spin-up.log`・`<候補>.log`・`<候補>.index.tsv`・`readings/`・`out/` |
| `SHA256SUMS` | 415 行。415 件すべて一致 |
| 読み取り | 索引 100 / 100 / 119 / 119 行。空でない stream ファイル 90 / 90 / 99 / 99 件 |
| 保存ファイル | 候補ごとに 6 件（内容のあるもの） |

記録作成時に行った照合:

1. `SHA256SUMS` の全件を再計算し、一致を確認した。
2. 候補ごとに索引の各行を順にたどり、結合ログの該当ブロック（コマンド・stream のパス・stdout・stderr・終了コード）が、
   ZIP 内の stream ファイルとバイト単位で一致することを確認した。438 件すべて一致、順序の乱れ・重複・索引にない stream ファイルはなかった。
3. ZIP にない stream は空として扱い、結合ログの該当部分も空であることを確認した。空の stream は artifact として回収されておらず、run.json の `unlisted_streams_verified_empty` に列挙されている。
4. 結合ログ末尾の索引の写しが、索引ファイルと一致することを確認した。
5. 証拠の中に API key・token・password などの値がないことを語句で検索して確認した。該当したのは基準版スクリプトの変数名（`OUTPUT_TOKEN`）だけである。

ZIP に含まれないもの: venv の中身、fixture、helper スクリプト、#171 の証拠。helper の本文は実験 commit の設定にある。CircleCI 上の artifact は E01 で 2,310 件あった（記録作成時の API 結果）。
計画が採用した保存期間（artifact 30 日・pipeline データ 90 日）に依存しないよう、判断に必要な値は本書の本文と付録に埋め込んだ。実測と ZIP の受領は同じ日である。
再照合では、付録 A の438件の終了コード・コマンド、本文228セルの終了コード、保存内容6件×4候補と対応する stdout が一致した。付録 B の抜粋・短い出力の表示では一部の連続空行や末尾空行が省略される。元のバイト列は ZIP の stream・結合ログ・ハッシュで照合する。

## 16. 完了条件のレビュー用対応表

以下はレビュー用の照合結果であり、Redmine のチェック状態・status・進捗を変更した記録ではない。「材料あり」は合格の宣言ではない。

| 完了条件 | 照合結果 | 根拠となる観測名・節 | 未確認・判定不能（§12） |
| --- | --- | --- | --- |
| C1 | 材料あり。承認 → #5544 終了 → hold → 開始の順を #171・#172 の両方で日時により追跡できる。入力版・hash は 4 job で一致。候補は M1 の同定と一致 | `revision-sha`、`config-hash`、`worktree-clean`、`revision-branch`、`commit-subject`、`pipeline`、`candidate-role`、M-00 の各読み取り。§2〜§4 | 人間自身の起動前照合記録、hold 承認者の実名との対応 |
| C2 | 一部に判定不能あり。別 run step をまたぐ参照先、子シェル内の PATH 変更、BASH_ENV の複数回追記・順次利用を観測 | `producer-*`、`consumer-*`、`after-consumer-path-change-*`、`bash-env-*`、`value-*`、`path-after-two-appends`、`resolve-after-two-appends`。§5、§6 | 既存 BASH_ENV 内容の保全（判定不能）。独立した利用者 step の効果、step のシェル自身の PATH。明示方式での失敗例の lint |
| C3 | 一部未確認あり。PATH の競合、実行ファイルの場所、venv でのモジュール起動、裸のコマンドの終了値を記録 | `show-version-script`、`execute-script-listing`、`execute-script-lint`、`selected-a-module-file`、`selected-*-module-launch`、`destination-not-on-path`。§7 | 基底環境でのモジュール起動（`base-module-launch` は別対象）。列挙・lint を実行した導入物、Orb 経由の不在時の動作 |
| C4 | 材料あり（一部判定不能）。判定する command、得られる入力、機械的に拒否できる範囲を区別できる | `install-inputs`、`execute-inputs`、`out-*`、`out-listing`。§8。#5544 の配置記録は M1 記録 §6〜§8 | 対象・設定と同じ出力先の専用拒否（判定不能）。M2-04 で動いた yamllint の版 |
| C5 | 一部未確認あり。必要ライブラリ、実行方法、不足時の診断、保存無効時の依存なし、E01/E02 の分離を記録 | `helper-contract`、`save-*`、`venv-helper-modules`、`isolation-*`、`saved-files`。§9 | 基底 python3 での保存（2 案が別対象になる条件）。E03/E04 の分離（判定不能） |
| C6 | 材料あり（一部未実行）。出力の分離、新規ファイル、衝突拒否、優先順位を直接観測。コードと診断を一覧化 | `clean-*`、`lint-error-save-enabled`、`warning-only-*`、`collision-refused`、`unwritable-parent`、`current-uid`、`control-*`、`save-fails-after-*`、`limited-results-absent`、`temporary-files-left`、`saved-bytes`、`saved-heads`。§10、§11 | 警告非表示のみのケース。環境選択の失敗・yamllint 不在時の Orb の診断。M2-06 で動いた yamllint の版 |
| C7 | 未完了。ロードマップ v1 の D03・D05・D07・D08 と配置制約への対応は §13 に整理。記録作成時の main に測定設定の混入なし | §12〜§15、付録 A・B | C3 の実行対象と C5 の2案が異なる条件での比較が不足。C2・C6 の不足も追加測定の対象 |

#172 の各観測は上記の範囲で採用する。後続の方式判断に必要な C3・C5 の実測を補った後で、残る各項目と C7 を再評価する。

## 17. 残る手続き

1. #172 の履歴記録を通常の作業ブランチからレビューして main に反映する。
2. 追加測定の目的・ケース・計画版・実験 commit・設定 SHA-256 を対応付け、計画 §11.1 に人間の承認と日時を記録してから実験ブランチを push する。経路はローカル → Git サーバー → GitHub。
3. 実行後は pipeline 番号・候補・ケース別に別の実測欄を設ける。§2 は #172 の実行記録として保持し、#5545 の C7 は追加証拠から改めて判定する。

<a id="m2-176"></a>

## 18. #176 追加実測と #5545 の総合照合

2026-11-19 JST、承認済みの追加測定で E01〜E04 の4ジョブが成功した。#172 で判定できなかった実行先を、#176 では実際に動いたプロセスと対照実行から特定した。ChatGPT Work が原本を照合して追記案を作成した。Claude はその版（文書 SHA-256 `75b597a65ecc30c301f2ad479eb3ca9d05f23c1b77d80819656fe4b3d3c84455`）を独立にレビューし、必須修正なし・追加測定不要と判定した。本節にはレビューで推奨された記述の修正3件を反映した。§1〜§17 と付録 A・B は #172 時点の記録として読める。追加測定の比較結果は §18.2〜§18.5、完了条件の判定案は §18.6 にまとめた。

### 18.1 承認・実行・証拠の対応

| 項目 | #176 で照合した値 |
| --- | --- |
| 計画 | 追加案 `4c6a9f219f64ad1e89c420a67dd96cda209a75d7` の直後に承認を記録した `main` の `bb1d5008b0fc31f0b319ce93eff2f7a57a80df02`。計画書の SHA-256 は `9db925667c03c7d542d87e0672b333360e55fa62b3cecd2cb7d233d596a29264` |
| 比較の元資料 | #5544 終了時の M1 は `c22645388712e507a138d77127988192fb4f80e9`（journal 11297）。#172 の計画は `b49d6dfdbd14feb98cfc19e52ed99a912f0f739b`、照合済み M2 記録は `7fe29ca67cb4f2e3620ca15228fa9cc4dda7602f` |
| 実験 branch と commit | `exp/230-m2` の `be97f874b99fd99582ae15434011910741c53200`。親は #172 の `ebd63fd1426dab201f5190b7e337e65eed09ca5a`、親との差分は `.circleci/config.yml` のみ |
| 設定 SHA-256 | #172 は `4ac54e23315313794f32f0052bf5f0e00eac092231c4cbbfb604d66bfbce2375`、#176 は `b7b030636692e34f342a2d30c0df2c4a1720b7b097a88c439703a755c07a1512`。#176 は承認値・Git の設定・CircleCI の source・4ジョブの checkout で一致 |
| 計画 §11.2 の #5545 追加実行行 | 計画 `bb1d500`、実験 `be97f874`、設定 `b7b03063…`（上記の完全値）。hold 成功は 2026-11-19 00:23:05.930 JST、最初の compute job 開始は同日 00:23:07.871 JST。記録先は本節 |
| Pipeline / workflow | #176 `dec5b822-c1c2-4e88-a116-a7d33d805075`、`measure-m2-supplement` `ddc58199-1aa5-4865-a24c-7a05587928c9`、success。承認 hold 1件と small の compute 4件 |
| Hold 確認 | job 2533 の `approved_by` は `d3d64a41-7b9c-4cce-97a9-48f8a292cb52`。時刻は successful hold の `stopped_at` を使用。CircleCI のアカウントと Redmine ID 3 との対応、人間による起動前 remote 照合の操作時刻は公開証拠の範囲外 |
| 計画・設定の分離 | 比較時の `main` は `bb1d500`。技術基準 `2fc343180c9e13660889ac5643b75fbcabd513ea` からの差分は計画書・M1 記録・M2 記録の3ファイル。両版の通常 `.circleci/config.yml` の SHA-256 は `bbaca8dce8cae7118dcc720aa49475ca8cb3bf9f507b6f7d23f0ad4aad80941a`。今回の追記の対象は M2 記録1ファイル |

時刻はすべて JST。#5544 は 11月17日 23:04:40 に終了した。#171 のパラメーター形式エラーと、同じ入力版で値を訂正した #172 の経緯は §2 にある。#171 は測定件数に含めず、#172 は当時の観測条件の範囲で利用する。

| 出来事 | 時刻 | 根拠 |
| --- | --- | --- |
| 追加測定1回に対する人間の承認 | 11月18日 23:30（受領時計 23:30:48） | `main` の H9 §11.1 |
| 実験 branch の push に対応する #175 作成 | 11月19日 00:15:02.207 | webhook。処理済み設定の workflow・job はともに0件 |
| 追加測定 #176 作成 | 00:22:59.066 | API trigger。処理済み設定で4ジョブの承認 commit・hash と各候補 ID を照合 |
| hold 開始 → 成功 | 00:22:59.673 → 00:23:05.930 | workflow jobs の job 2533 |
| 最初の compute job 開始 → 最後の終了 | 00:23:07.871 → 00:24:42.116 | いずれも E03。workflow も同時刻に成功終了 |
| 証拠回収 | 00:29:49 | ChatGPT Work が4組を当日取得した時刻。保存した原本は §18.7 に掲載 |

4候補すべてで `revision-sha`、`config-hash`、`worktree-clean`、`final-checkout` を照合した。使用した Python の minor・実行ユーザー・CPU・使用 stdlib の標識は M1 §4 と対応する。E03/E04 は利用側の apt 準備後の候補条件である。

| 候補・ジョブ | image / OS | 基底 Python / UID | `python` / PEP 668 標識 | 開始 → 終了（JST） |
| --- | --- | --- | --- | --- |
| E01 / 2534 | `cimg/python:3.14` / Ubuntu 24.04 | 3.14.10 / 1001 | 有 / 無 | 00:23:08.419 → 00:23:34.257 |
| E02 / 2535 | `cimg/python:3.13` / Ubuntu 22.04 | 3.13.18 / 1001 | 有 / 無 | 00:23:08.469 → 00:23:33.383 |
| E03 / 2537 | `ubuntu:22.04` / Ubuntu 22.04 | 3.10.12 / 0 | 無 / 無 | 00:23:07.871 → 00:24:42.116 |
| E04 / 2536 | `ubuntu:24.04` / Ubuntu 24.04 | 3.12.3 / 0 | 無 / 有 | 00:23:08.364 → 00:23:45.418 |

全候補が x86_64。Spin up ログで image のタグを確認した。完全な image digest は取得できず、イメージのバイト同一性までは判断できない。[計画版](https://github.com/circleci-orbs-mamono210/yamllint/commit/bb1d5008b0fc31f0b319ce93eff2f7a57a80df02)・[実験版](https://github.com/circleci-orbs-mamono210/yamllint/commit/be97f874b99fd99582ae15434011910741c53200)・[workflow](https://app.circleci.com/pipelines/gh/circleci-orbs-mamono210/yamllint/176/workflows/ddc58199-1aa5-4865-a24c-7a05587928c9)・[処理済み設定](https://circleci.com/api/v2/pipeline/dec5b822-c1c2-4e88-a116-a7d33d805075/config)・[job 一覧](https://circleci.com/api/v2/workflow/ddc58199-1aa5-4865-a24c-7a05587928c9/job)。

### 18.2 別 step への引き継ぎ（C2・D03）

ここで A は `/tmp/m2-work/A` の yamllint 1.38.0、B は `/tmp/m2-work/B` の 1.37.1。S1〜S6 は CircleCI の別々の run step で、`*-shell` は各 step 自身のシェルから読んだ。以下は4候補で共通した。

| 実 step | 既存の PATH による解決 | 明示した実行先・利用者設定の観測 |
| --- | --- | --- |
| S1 新しい利用 step | yamllint 不在 | 保存しておいた A の絶対パスから版表示 1.38.0、3ファイル列挙、警告とエラーを含む lint は終了 1 |
| S2 利用者が B を export | 通常の版表示は B 1.37.1 | A → B → A を明示すると 1.38.0 → 1.37.1 → 1.38.0 |
| S3 次の利用 step | yamllint 不在に戻る | 明示 A は 1.38.0。この時点の native BASH_ENV ファイルは全候補で不在。利用者側のマーカーと B の PATH を書いた |
| S4 既存内容を読み A を追記 | 追記前は B と `consumer-r1` | 利用者が先に書いた71バイトの長さと SHA-256 を記録 |
| S5 A の追記後 | A が先頭。既存の版表示は 1.38.0 | 利用者の先頭71バイトの hash とマーカーが一致。ここで B を追記 |
| S6 B の追記後 | PATH の先頭3要素は B/bin → A/bin → B/bin。B/bin が2回現れ、既存の版表示は 1.37.1 | 同じ71バイトとマーカーが再度一致。A の絶対パス指定は 1.38.0 |

根拠は `explicit-{consumer-shell,show,list,tree-lint}`、`user-export-*`、`post-export-*`、`consumer-owned-shell`、`remember-consumer-prefix`、`after-{A,B}-shell`、`prefix-after-{A,B}`、`existing-route-after-{A,B}`、`explicit-A-after-B`。既存内容の保全を示せるのは制御した71バイト。#172 §6 の引用方法による値の再評価は引き続き制約になる。

### 18.3 実際に起動した yamllint とモジュール（C3・D05）

後続の比較では引き継ぎ前に記録した基底 PATH に戻し、子 bash を起動する前に BASH_ENV を外した。元の `show-version.sh` と `execute.sh` の lint・listing について、console script のプロセス自身が記録した `argv0`、解決された CLI、`sys.executable`、`sys.prefix`、モジュールファイル、版を照合した。

| 比較 | 表示・lint・listing の3経路 | 同じ Python のモジュール起動 |
| --- | --- | --- |
| A を PATH 先頭にする | 全て A の `bin/yamllint` と `bin/python`、prefix は A、モジュールは A 配下の `site-packages/yamllint/__init__.py`、1.38.0 | A の `bin/python -m yamllint --version` は 0、1.38.0 |
| B を PATH 先頭にする | 全て B の同じ相対位置、1.37.1 | B の同じ起動は 0、1.37.1 |
| 捕捉した基底 PATH / 基底 Python | CLI の検索は 1、Orb の3経路は各127。4候補すべてで `yamllint: command not found` | 基底 Python の import と `-m yamllint --version` は各1。`No module named yamllint` |

`route-{A,B}-{show,lint,listing}` の計24組は、計測の有無で終了コード・stdout・stderr が一致した。個々のモジュールパスと基底・venv の prefix は `module-{base,A,B}-{file,launch}` と `traces/route-*.jsonl` にある。不在の CLI または Python の絶対パスを指定すると各127、同時に利用可能だった B の直接指定は 0・1.37.1。これは明示パスを指定する比較用呼び出しであり、現行 Orb の公開入力には環境選択パラメーターがない。

### 18.4 保存補助に使われた Python（C5・D05）

yamllint を A の 1.38.0 に固定した。現行の保存処理の prepare / forward / finalize の内部から実行 Python と `sys.flags.isolated` を読み、同じ条件で観測コードを外して再度実行した。全4候補・両経路で終了 0、警告の stdout は79バイト、stderr は空。計測あり・なしの保存ファイルは stdout とバイト単位で一致した。

| 候補 | 基底 PATH の python3 → 実行 Python | A を使う保存処理 | 作業ディレクトリの `select.py` と分離 |
| --- | --- | --- | --- |
| E01 | pyenv の shim → `/home/circleci/.pyenv/versions/3.14.10/bin/python3` | `/tmp/m2-work/A/bin/python3` | 基底・A とも通常はローカルを import、`-I` は標準の拡張モジュール |
| E02 | pyenv の shim → `/home/circleci/.pyenv/versions/3.13.18/bin/python3` | 同上 | 同上 |
| E03 | `/usr/bin/python3` | 同上 | 通常・`-I` とも組み込み `select` |
| E04 | `/usr/bin/python3` | 同上 | 通常・`-I` とも組み込み `select` |

基底側は `prefix == base_prefix`、A 側は `prefix == /tmp/m2-work/A` で `base_prefix` と異なる。全24回の helper プロセスで isolated フラグは 1、`os`・`select`・`stat`・`sys` の取得元を記録した。E03/E04 はフラグとモジュールの実体を確認できたが、この組み込みモジュールではカレントディレクトリの排除を見分けられない。PATH から python3 を外すと保存有効は起動前に2（`python3 was not found on PATH`）、保存無効は0。根拠は `save-{base,venv}*`、`absent-python-{on,off}`。

### 18.5 出力・失敗時の優先順位（C6・D07）

下表の終了値は計測ラッパーが捕捉した Orb プロセスの値。CircleCI で実際に失敗状態となった step を示す観測は、公開後直接確認の範囲で別途扱う。全候補で A の使用を確認した。

| 入力 | 保存無効の終了 | 保存有効の終了 | stdout / 保存ファイルのバイト数 |
| --- | ---: | ---: | ---: |
| clean | 0 | 0 | 0 |
| lint エラー | 1 | 1 | 103 |
| 警告のみ | 0 | 0 | 79 |
| 警告のみ・strict | 2 | 2 | 79 |
| 警告非表示・strict なし | 0 | 0 | 0 |
| 警告非表示・strict あり | 2 | 2 | 0 |

各行で保存の有無による stdout・stderr の差はなく、stderr は空。保存有効では0バイトの場合も新規ファイルが作成された。根拠は `contract-{clean,error,warning,strict,hidden,strict-hidden}-{off,on}`、CLI の trace と保存ファイル。

| 操作・失敗箇所 | 実測した戻り値と診断 |
| --- | --- |
| 実行先を明示した CLI/Python が存在しない | いずれも127。`No such file or directory`。別に利用可能な B への暗黙の切替は起きなかった |
| CLI 不在の現行 Orb の表示・lint・listing／保存付き lint | 全て127。`yamllint: command not found`。保存付きは `no result file was created` も stderr に出力し、結果ファイルは残らなかった |
| CLI 不在かつ不正な入力 | targets が単独の `-` なら2・`standalone '-' is not supported`、2種類の設定を同時指定すると2・`config_file and config_data cannot both be non-empty`。どちらも起動より先に拒否 |
| lint 成功後の書き込み失敗 | 警告のみの対照は0。1,024バイトの書き込み制限を掛けると2・`File too large`。対照と同じ5,239バイトの stdout を維持 |
| lint エラー後の書き込み失敗 | 対照も制限時も1。制限時の stderr に同じ書き込み失敗が出た。対照と同じ6,583バイトの stdout を維持 |

制限時はいずれも最終ファイルを作成せず、一時ファイルの一覧も空だった。各候補で保存した12ファイルすべての実バイトを対応する stdout と照合した。`missing-cli-*`、`selection-*`、`priority-{warnings,errors}-{control,limited}`、`evidence-check` で判断を追える。

### 18.6 完了条件と後続判断

| 条件 | #172 と #176 を合わせた判定案 | 適用限界・後続へ渡すこと |
| --- | --- | --- |
| C1 | §2・§18.1 の実行順、起動時に展開された承認値と4候補の checkout、M1 成果物・終了 journal の対応を確認。追加1回は承認後に開始 | #171 の入力訂正、#172 の実測、#175 の空の設定、#176 の実測を別々に記録。hold の実名と起動前の人間の操作時刻は未確認 |
| C2 | 実 step をまたぐ明示方式と BASH_ENV 方式、利用者の PATH 変更・複数回の追記・制御した既存内容を比較できた（§6・§18.2） | BASH_ENV の追記後、既存スクリプトで直接確認したのは版表示。lint・列挙の実行先は §18.3 の PATH を指定した比較に基づく。引用・値の再評価の境界は #172 §6 |
| C3 | A と B それぞれで表示・lint・listing の実行プロセスを同定し、基底 Python の import・起動失敗と A/B の成功を比較できた（§18.3） | 基底環境に yamllint を導入した状態でのモジュール起動は M2 では未測定。#172 の基底と称した読み取りを再分類した経緯は §7・§12 に記録した |
| C4 | #5544 の配置比較（内側で列挙3件→5件）と #172 §8 の起動前拒否6件（各2）を利用し、機械的に判定できる範囲を区別できた | install は版のみを受け、execute に導入先の情報がない。対象・設定と同一の既存ファイルは「既存」の検査が先行する。#176 での再測定対象外 |
| C5 | yamllint を固定し、実行パスと `sys.prefix` が異なる基底・venv の保存用 Python を比較できた。隔離、4モジュール、保存無効時の依存、Python 不在時の診断を確認（§18.4） | E03/E04 では組み込み select のため局所 import の違いを実証できる範囲に限界がある |
| C6 | 通常・警告・strict・警告非表示、入力拒否、明示選択の失敗、CLI 不在、lint と保存失敗の優先順位を、コード・診断・ファイルに対応付けた（§10、§11、§18.5） | Orb プロセスの終了値と CircleCI step の表示を分けて扱う |
| C7 | D03＝§18.2、D05＝§18.3〜§18.4、D07＝§18.5、D08＝下記の利用側直接確認への引き継ぎ、配置＝§8・C4。#172 で不足した C3/C5 の比較がそろい、Phase 1 の技術判断資料は充足と判定する | 最終レビュー、通常ブランチからの実測記録の main 反映、成果物 commit の #5545 journal への記録で永続化する |

D03・D05 の方式・採否は #5547 に渡す。D07 では同じ終了値になる原因を診断で識別し、D08 では公表された版を利用する独立したプロジェクトで、どの経路・代表環境と意図的に失敗する job を確認するかを決める。#176 で得たのは基準スクリプトと実験設定の結果である。#5545 の追加比較のための CI 再実行は不要と判断した。

### 18.7 回収した原本と照合方法

各ジョブの Artifacts にある `measurement-m2-supplement/E0n.tar.gz` と同名の `.sha256` を回収した。下表はアーカイブ本体の SHA-256 と内部 `SHA256SUMS` の照合件数。読み取りは、索引・結合ログ・空を含む stdout/stderr 原本をバイト単位で照合した件数である。

| 候補 / ジョブ | 読み取り | 内部 SHA-256 | アーカイブ SHA-256 |
| --- | ---: | ---: | --- |
| E01 / [2534](https://app.circleci.com/pipelines/gh/circleci-orbs-mamono210/yamllint/176/workflows/ddc58199-1aa5-4865-a24c-7a05587928c9/jobs/2534) | 137 | 314 | `13d628b5254b18cccb7f0653f02b19666be1f39c2df36bc643e971f2c1d65d0b` |
| E02 / [2535](https://app.circleci.com/pipelines/gh/circleci-orbs-mamono210/yamllint/176/workflows/ddc58199-1aa5-4865-a24c-7a05587928c9/jobs/2535) | 137 | 314 | `b5fd9aadf5a383bb25366410e75d27042fc475289d4a421e9661fddcb45f0287` |
| E03 / [2537](https://app.circleci.com/pipelines/gh/circleci-orbs-mamono210/yamllint/176/workflows/ddc58199-1aa5-4865-a24c-7a05587928c9/jobs/2537) | 156 | 352 | `258126b647a0f05cd990a12c8bf1956d984ed4d44c5c1b93af84e076f2b61a12` |
| E04 / [2536](https://app.circleci.com/pipelines/gh/circleci-orbs-mamono210/yamllint/176/workflows/ddc58199-1aa5-4865-a24c-7a05587928c9/jobs/2536) | 156 | 352 | `7b9caf5f3c4e073e1be2595d13017f725defc505b546e9e885c44bb5a4e03f27` |

4個の外部ハッシュと内部1,332件が一致した。586件（137＋137＋156＋156）のコマンド・終了値・stdout/stderr を照合し、全1,172個の stream 原本が存在した。各候補の自己検査も `evidence_errors=[]` だった。

回収物は `yamllint-5545-m2-results-176.zip`。展開すると `evidence/artifacts/` に CircleCI の原本8ファイル、`evidence/run.json` に実行・step のメタデータ、`evidence/observations.tsv` に全件の索引がある。各アーカイブ内の `readings/`・`traces/`・`saved/` に出力と実ファイルを保存した。`python3 verify.py` で通信せずに原本の整合性と上記の比較を再検証できる。#172 原本の別 ZIP と照合方法は §15 に記録した。

## 付録 A. 全読み取りの索引

候補ごとの job URL は §3。各読み取りの原文は ZIP の `<候補>/measurement-m2/<候補>.log`、
stream は `<候補>/measurement-m2/readings/<候補>/<観測名>.stdout` / `.stderr`。終了コードは `<候補>.index.tsv` と照合済み。
`-` はその候補に読み取りがないことを表す（E01/E02 には準備後の同定がなく、E03/E04 は準備前に stdlib の標識を読めない）。

### A.1 終了コード

| 観測名 | ケース | E01 | E02 | E03 | E04 |
| --- | --- | --- | --- | --- | --- |
| `id-user-before-preparation` | M-00 | 0 | 0 | 0 | 0 |
| `uname-before-preparation` | M-00 | 0 | 0 | 0 | 0 |
| `os-release-before-preparation` | M-00 | 0 | 0 | 0 | 0 |
| `which-python-before-preparation` | M-00 | 0 | 0 | 1 | 1 |
| `which-python3-before-preparation` | M-00 | 0 | 0 | 1 | 1 |
| `which-pip-before-preparation` | M-00 | 0 | 0 | 1 | 1 |
| `which-pip3-before-preparation` | M-00 | 0 | 0 | 1 | 1 |
| `which-git-before-preparation` | M-00 | 0 | 0 | 1 | 1 |
| `which-ssh-before-preparation` | M-00 | 0 | 0 | 1 | 1 |
| `which-yamllint-before-preparation` | M-00 | 1 | 1 | 1 | 1 |
| `python3-version-before-preparation` | M-00 | 0 | 0 | 127 | 127 |
| `stdlib-before-preparation` | M-00 | 0 | 0 | 127 | 127 |
| `venv-state-before-preparation` | M-00 | 0 | 0 | 127 | 127 |
| `pip-version-before-preparation` | M-00 | 0 | 0 | 127 | 127 |
| `marker-sysconfig-before-preparation` | M-00 | 2 | 2 | - | - |
| `marker-usrlib-before-preparation` | M-00 | 0 | 2 | 2 | 2 |
| `marker-head-before-preparation` | M-00 | 0 | 1 | 1 | 1 |
| `apt-update` | M-00 | - | - | 0 | 0 |
| `apt-install` | M-00 | - | - | 0 | 0 |
| `apt-versions` | M-00 | - | - | 0 | 0 |
| `id-user-after-preparation` | M-00 | - | - | 0 | 0 |
| `uname-after-preparation` | M-00 | - | - | 0 | 0 |
| `os-release-after-preparation` | M-00 | - | - | 0 | 0 |
| `which-python-after-preparation` | M-00 | - | - | 1 | 1 |
| `which-python3-after-preparation` | M-00 | - | - | 0 | 0 |
| `which-pip-after-preparation` | M-00 | - | - | 0 | 0 |
| `which-pip3-after-preparation` | M-00 | - | - | 0 | 0 |
| `which-git-after-preparation` | M-00 | - | - | 0 | 0 |
| `which-ssh-after-preparation` | M-00 | - | - | 0 | 0 |
| `which-yamllint-after-preparation` | M-00 | - | - | 1 | 1 |
| `python3-version-after-preparation` | M-00 | - | - | 0 | 0 |
| `stdlib-after-preparation` | M-00 | - | - | 0 | 0 |
| `venv-state-after-preparation` | M-00 | - | - | 0 | 0 |
| `pip-version-after-preparation` | M-00 | - | - | 0 | 0 |
| `marker-sysconfig-after-preparation` | M-00 | - | - | 2 | 0 |
| `marker-usrlib-after-preparation` | M-00 | - | - | 2 | 0 |
| `marker-head-after-preparation` | M-00 | - | - | 1 | 0 |
| `candidate-role` | M-00c | 0 | 0 | 0 | 0 |
| `candidate-pip` | M-00c | 0 | 0 | 0 | 0 |
| `revision-sha` | revision gate | 0 | 0 | 0 | 0 |
| `config-hash` | revision gate | 0 | 0 | 0 | 0 |
| `worktree-clean` | revision gate | 0 | 0 | 0 | 0 |
| `revision-branch` | revision gate | 0 | 0 | 0 | 0 |
| `commit-subject` | revision gate | 0 | 0 | 0 | 0 |
| `pipeline` | revision gate | 0 | 0 | 0 | 0 |
| `venv-a-create` | M2-00 | 0 | 0 | 0 | 0 |
| `venv-a-install` | M2-00 | 0 | 0 | 0 | 0 |
| `venv-b-create` | M2-00 | 0 | 0 | 0 | 0 |
| `venv-b-install` | M2-00 | 0 | 0 | 0 | 0 |
| `slim-bin` | M2-00 | 0 | 0 | 0 | 0 |
| `fixture-sizes` | M2-00 | 0 | 0 | 0 | 0 |
| `producer-same-step` | M2-01 | 0 | 0 | 0 | 0 |
| `producer-path` | M2-01 | 0 | 0 | 0 | 0 |
| `consumer-path` | M2-01 | 0 | 0 | 0 | 0 |
| `consumer-inherited` | M2-01 | 0 | 0 | 0 | 0 |
| `consumer-explicit-version` | M2-01 | 0 | 0 | 0 | 0 |
| `consumer-explicit-listing` | M2-01 | 0 | 0 | 0 | 0 |
| `consumer-explicit-lint` | M2-01 | 0 | 0 | 0 | 0 |
| `after-consumer-path-change-resolved` | M2-01 | 0 | 0 | 0 | 0 |
| `after-consumer-path-change-explicit` | M2-01 | 0 | 0 | 0 | 0 |
| `bash-env-name` | M2-02 | 0 | 0 | 0 | 0 |
| `bash-env-remember` | M2-02 | 0 | 0 | 0 | 0 |
| `bash-env-after-append` | M2-02 | 0 | 0 | 0 | 0 |
| `bash-env-later-path` | M2-02 | 0 | 0 | 0 | 0 |
| `bash-env-later-resolve` | M2-02 | 0 | 0 | 0 | 0 |
| `bash-env-marker-kept` | M2-02 | 0 | 0 | 0 | 0 |
| `bash-env-prefix-unchanged` | M2-02 | 0 | 0 | 0 | 0 |
| `bash-env-shape-now` | M2-02 | 0 | 0 | 0 | 0 |
| `bash-env-second-append` | M2-02 | 0 | 0 | 0 | 0 |
| `value-unquoted` | M2-02 | 0 | 0 | 0 | 0 |
| `value-quoted` | M2-02 | 0 | 0 | 0 | 0 |
| `path-after-two-appends` | M2-02 | 0 | 0 | 0 | 0 |
| `resolve-after-two-appends` | M2-02 | 0 | 0 | 0 | 0 |
| `show-version-script` | M2-03 | 0 | 0 | 0 | 0 |
| `execute-script-listing` | M2-03 | 0 | 0 | 0 | 0 |
| `execute-script-lint` | M2-03 | 0 | 0 | 0 | 0 |
| `selected-a-module-file` | M2-03 | 0 | 0 | 0 | 0 |
| `selected-a-module-launch` | M2-03 | 0 | 0 | 0 | 0 |
| `selected-b-module-launch` | M2-03 | 0 | 0 | 0 | 0 |
| `destination-not-on-path` | M2-03 | 127 | 127 | 127 | 127 |
| `base-module-launch` | M2-03 | 0 | 0 | 0 | 0 |
| `install-inputs` | M2-04 | 0 | 0 | 0 | 0 |
| `execute-inputs` | M2-04 | 0 | 0 | 0 | 0 |
| `out-inside-target-dir` | M2-04 | 2 | 2 | 2 | 2 |
| `out-equal-target-file` | M2-04 | 2 | 2 | 2 | 2 |
| `out-equal-config-file` | M2-04 | 2 | 2 | 2 | 2 |
| `out-parent-missing` | M2-04 | 2 | 2 | 2 | 2 |
| `out-already-exists` | M2-04 | 2 | 2 | 2 | 2 |
| `out-parent-not-a-directory` | M2-04 | 2 | 2 | 2 | 2 |
| `out-dotdot` | M2-04 | 1 | 1 | 1 | 1 |
| `out-outside-targets` | M2-04 | 0 | 0 | 0 | 0 |
| `out-listing` | M2-04 | 0 | 0 | 0 | 0 |
| `helper-contract` | M2-05 | 0 | 0 | 0 | 0 |
| `save-with-path-python3` | M2-05 | 0 | 0 | 0 | 0 |
| `save-without-python3` | M2-05 | 2 | 2 | 2 | 2 |
| `save-with-only-venv-python3` | M2-05 | 0 | 0 | 0 | 0 |
| `save-disabled-without-python3` | M2-05 | 0 | 0 | 0 | 0 |
| `venv-helper-modules` | M2-05 | 0 | 0 | 0 | 0 |
| `save-with-local-select` | M2-05 | 0 | 0 | 0 | 0 |
| `isolation-without-I` | M2-05 | 1 | 1 | 0 | 0 |
| `isolation-with-I` | M2-05 | 0 | 0 | 0 | 0 |
| `saved-files` | M2-05 | 0 | 0 | 0 | 0 |
| `clean-save-disabled` | M2-06 | 0 | 0 | 0 | 0 |
| `clean-save-enabled` | M2-06 | 0 | 0 | 0 | 0 |
| `lint-error-save-enabled` | M2-06 | 1 | 1 | 1 | 1 |
| `warning-only-not-strict` | M2-06 | 0 | 0 | 0 | 0 |
| `warning-only-strict` | M2-06 | 2 | 2 | 2 | 2 |
| `warning-only-strict-no-warnings` | M2-06 | 2 | 2 | 2 | 2 |
| `collision-refused` | M2-06 | 2 | 2 | 2 | 2 |
| `saved-bytes` | M2-06 | 0 | 0 | 0 | 0 |
| `saved-heads` | M2-06 | 0 | 0 | 0 | 0 |
| `current-uid` | M2-06 | 0 | 0 | 0 | 0 |
| `unwritable-parent` | M2-06 | 2 | 2 | 0 | 0 |
| `control-lint-ok-many-warnings` | M2-06 | 0 | 0 | 0 | 0 |
| `control-lint-error-many` | M2-06 | 1 | 1 | 1 | 1 |
| `save-fails-after-lint-ok` | M2-06 | 2 | 2 | 2 | 2 |
| `save-fails-after-lint-error` | M2-06 | 1 | 1 | 1 | 1 |
| `limited-results-absent` | M2-06 | 2 | 2 | 2 | 2 |
| `temporary-files-left` | M2-06 | 0 | 0 | 0 | 0 |
| `main-not-touched` | M2-07 | 0 | 0 | 0 | 0 |

読み取りの件数: E01 100 件（非 0 は 21 件）、E02 100 件（非 0 は 23 件）、E03 119 件（非 0 は 35 件）、E04 119 件（非 0 は 32 件）。

### A.2 コマンド

観測 helper が保存した shell-escaped 表記であり、ここで再実行する指示ではない。候補によって表記が異なるものは候補名を付けて並べた。

```text
id-user-before-preparation :: id -u
uname-before-preparation :: uname -m
os-release-before-preparation :: cat /etc/os-release
which-python-before-preparation :: command -v python
which-python3-before-preparation :: command -v python3
which-pip-before-preparation :: command -v pip
which-pip3-before-preparation :: command -v pip3
which-git-before-preparation :: command -v git
which-ssh-before-preparation :: command -v ssh
which-yamllint-before-preparation :: command -v yamllint
python3-version-before-preparation :: python3 -VV
stdlib-before-preparation :: python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)
venv-state-before-preparation :: python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)
pip-version-before-preparation :: python3 -m pip --version
marker-sysconfig-before-preparation [E01] :: ls -l /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED
marker-sysconfig-before-preparation [E02] :: ls -l /home/circleci/.pyenv/versions/3.13.18/lib/python3.13/EXTERNALLY-MANAGED
marker-usrlib-before-preparation :: /bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED
marker-head-before-preparation :: /bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED
apt-update :: apt-get update
apt-install :: apt-get install -y --no-install-recommends python3 python3-venv python3-pip git ca-certificates openssh-client
apt-versions :: dpkg-query -W -f \$\{Package\}\ \$\{Version\}\\n python3 python3-venv python3-pip git
id-user-after-preparation :: id -u
uname-after-preparation :: uname -m
os-release-after-preparation :: cat /etc/os-release
which-python-after-preparation :: command -v python
which-python3-after-preparation :: command -v python3
which-pip-after-preparation :: command -v pip
which-pip3-after-preparation :: command -v pip3
which-git-after-preparation :: command -v git
which-ssh-after-preparation :: command -v ssh
which-yamllint-after-preparation :: command -v yamllint
python3-version-after-preparation :: python3 -VV
stdlib-after-preparation :: python3 -c import\ sysconfig\;\ print\(sysconfig.get_path\(\"stdlib\"\)\)
venv-state-after-preparation :: python3 -c import\ sys\;\ print\(sys.prefix\,\ sys.base_prefix\,\ sys.prefix\ \!=\ sys.base_prefix\)
pip-version-after-preparation :: python3 -m pip --version
marker-sysconfig-after-preparation [E03] :: ls -l /usr/lib/python3.10/EXTERNALLY-MANAGED
marker-sysconfig-after-preparation [E04] :: ls -l /usr/lib/python3.12/EXTERNALLY-MANAGED
marker-usrlib-after-preparation :: /bin/bash -o pipefail -c ls\ -l\ /usr/lib/python3\*/EXTERNALLY-MANAGED
marker-head-after-preparation :: /bin/bash -o pipefail -c head\ -20\ /usr/lib/python3\*/EXTERNALLY-MANAGED
candidate-role :: python3 /tmp/meas/check-candidate.py
candidate-pip :: python3 -m pip --version
revision-sha :: git rev-parse HEAD
config-hash :: sha256sum .circleci/config.yml
worktree-clean :: git status --porcelain
revision-branch :: git rev-parse --abbrev-ref HEAD
commit-subject :: git log -1 --pretty=%s
pipeline :: /bin/bash -o pipefail -c printf\ \"pipeline=%s\ job=%s\ build_url=%s\ workflow=%s\\n\"\ \"\$\{MEAS_PIPELINE_NUMBER:-\}\"\ \"\$\{CIRCLE_JOB:-\}\"\ \"\$\{CIRCLE_BUILD_URL:-\}\"\ \"\$\{CIRCLE_WORKFLOW_ID:-\}\"
venv-a-create :: python3 -m venv /tmp/meas/venvA
venv-a-install :: /tmp/meas/venvA/bin/python -m pip install yamllint==1.38.0
venv-b-create :: python3 -m venv /tmp/meas/venvB
venv-b-install :: /tmp/meas/venvB/bin/python -m pip install yamllint==1.37.1
slim-bin :: /bin/bash -o pipefail -c ls\ -l\ /tmp/meas/slim
fixture-sizes :: /bin/bash -o pipefail -c du\ -sh\ /tmp/meas/fixtures/warnmany\ /tmp/meas/fixtures/errmany
producer-same-step :: /tmp/meas/venvA/bin/yamllint --version
producer-path :: /bin/bash -o pipefail -c printf\ \"PATH=%s\\n\"\ \"\$PATH\"
consumer-path :: /bin/bash -o pipefail -c printf\ \"PATH=%s\\n\"\ \"\$PATH\"
consumer-inherited :: /bin/bash -o pipefail -c command\ -v\ yamllint\ \|\|\ echo\ ABSENT
consumer-explicit-version :: /tmp/meas/venvA/bin/yamllint --version
consumer-explicit-listing :: /bin/bash -o pipefail -c /tmp/meas/venvA/bin/yamllint\ --list-files\ .\ \|\ sort
consumer-explicit-lint :: /tmp/meas/venvA/bin/yamllint tree/ok.yml
after-consumer-path-change-resolved :: /bin/bash -o pipefail -c export\ PATH=/tmp/meas/venvB/bin:\$PATH\;\ command\ -v\ yamllint\ \&\&\ yamllint\ --version
after-consumer-path-change-explicit :: /bin/bash -o pipefail -c export\ PATH=/tmp/meas/venvB/bin:\$PATH\;\ /tmp/meas/venvA/bin/yamllint\ --version
bash-env-name :: /bin/bash -o pipefail -c printf\ \"BASH_ENV=%s\\n\"\ \"\$\{BASH_ENV:-UNSET\}\"
bash-env-remember :: /tmp/meas/bash_env.sh remember
bash-env-after-append :: /tmp/meas/bash_env.sh shape
bash-env-later-path :: /bin/bash -o pipefail -c printf\ \"PATH=%s\\n\"\ \"\$PATH\"
bash-env-later-resolve :: /bin/bash -o pipefail -c command\ -v\ yamllint\ \&\&\ yamllint\ --version
bash-env-marker-kept :: /bin/bash -o pipefail -c printf\ \"MEAS_MARKER_KEPT=%s\\n\"\ \"\$\{MEAS_MARKER_KEPT:-UNSET\}\"
bash-env-prefix-unchanged :: /tmp/meas/bash_env.sh verify
bash-env-shape-now :: /tmp/meas/bash_env.sh shape
bash-env-second-append :: /tmp/meas/bash_env.sh shape
value-unquoted :: /bin/bash -o pipefail -c printf\ \"MEAS_VALUE=%s\\n\"\ \"\$\{MEAS_VALUE:-UNSET\}\"
value-quoted :: /bin/bash -o pipefail -c printf\ \"MEAS_VALUE_QUOTED=%s\\n\"\ \"\$\{MEAS_VALUE_QUOTED:-UNSET\}\"
path-after-two-appends :: /bin/bash -o pipefail -c printf\ \"PATH=%s\\n\"\ \"\$PATH\"
resolve-after-two-appends :: /bin/bash -o pipefail -c command\ -v\ yamllint\ \&\&\ yamllint\ --version
show-version-script :: /bin/bash -o pipefail -c $'\n    export PATH=/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:$PATH\n    /tmp/meas/show_version.sh\n    status=$?\n    printf "resolved=%s\\n" "$(command -v yamllint)"\n    exit "${status}"\n'
execute-script-listing :: /bin/bash -o pipefail -c export\ PATH=/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:\$PATH\;\ /tmp/meas/run_exec.sh\ \".\"\ \"\"\ \"\"\ false\ false\ true\ \"\"\ \|\ sort
execute-script-lint :: /bin/bash -o pipefail -c export\ PATH=/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:\$PATH\;\ /tmp/meas/run_exec.sh\ \"tree/ok.yml\"\ \"\"\ \"\"\ false\ false\ false\ \"\"
selected-a-module-file :: /tmp/meas/venvA/bin/python -c import\ yamllint\;\ print\(yamllint.__file__\,\ yamllint.APP_VERSION\)
selected-a-module-launch :: /tmp/meas/venvA/bin/python -m yamllint --version
selected-b-module-launch :: /tmp/meas/venvB/bin/python -m yamllint --version
destination-not-on-path :: /bin/bash -o pipefail -c export\ PATH=/usr/bin:/bin\;\ printf\ \"resolved=%s\\n\"\ \"\$\(command\ -v\ yamllint\ \|\|\ echo\ ABSENT\)\"\;\ yamllint\ --version
base-module-launch :: /bin/bash -o pipefail -c python3\ -m\ yamllint\ --version
install-inputs :: /bin/bash -o pipefail -c grep\ -n\ \"PARAM_\"\ \"\$\(cat\ /tmp/meas/repo_path\)/src/commands/install.yml\"
execute-inputs :: /bin/bash -o pipefail -c grep\ -n\ \"PARAM_\"\ \"\$\(cat\ /tmp/meas/repo_path\)/src/commands/execute.yml\"
out-inside-target-dir :: /tmp/meas/run_exec.sh tree tree/report.txt '' false false false ''
out-equal-target-file :: /tmp/meas/run_exec.sh tree/ok.yml tree/ok.yml '' false false false ''
out-equal-config-file :: /tmp/meas/run_exec.sh tree custom.yml custom.yml false false false ''
out-parent-missing :: /tmp/meas/run_exec.sh tree /tmp/meas/absent/report.txt '' false false false ''
out-already-exists :: /tmp/meas/run_exec.sh tree /tmp/meas/fixtures/custom.yml '' false false false ''
out-parent-not-a-directory :: /tmp/meas/run_exec.sh tree custom.yml/report.txt '' false false false ''
out-dotdot :: /tmp/meas/run_exec.sh tree /tmp/meas/out/../out/dotdot.txt '' false false false ''
out-outside-targets :: /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/report-ok.txt '' false false false ''
out-listing :: /bin/bash -o pipefail -c ls\ -l\ /tmp/meas/out
helper-contract :: /bin/bash -o pipefail -c grep\ -n\ \"command\ -v\ python3\\\|python3\ -I\\\|\^import\ \"\ \"\$\(cat\ /tmp/meas/repo_path\)/src/scripts/execute.sh\"
save-with-path-python3 [E01,E02] :: env -u BASH_ENV PATH=/tmp/meas/venvA/bin:/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:/home/circleci/.pyenv/shims:/home/circleci/.pyenv/bin:/home/circleci/.poetry/bin:/home/circleci/bin:/home/circleci/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/base.txt '' false false false ''
save-with-path-python3 [E03,E04] :: env -u BASH_ENV PATH=/tmp/meas/venvA/bin:/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/base.txt '' false false false ''
save-without-python3 :: env -u BASH_ENV PATH=/tmp/meas/slim /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/nopy.txt '' false false false ''
save-with-only-venv-python3 :: env -u BASH_ENV PATH=/tmp/meas/venvA/bin:/tmp/meas/slim /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/venvpy.txt '' false false false ''
save-disabled-without-python3 :: env -u BASH_ENV PATH=/tmp/meas/slim /tmp/meas/run_exec.sh tree/ok.yml '' '' false false false ''
venv-helper-modules :: /tmp/meas/venvA/bin/python -I -c import\ os\,\ select\,\ stat\,\ sys\;\ print\(\"modules\ ok\"\)
save-with-local-select [E01,E02] :: env -u BASH_ENV PATH=/tmp/meas/venvA/bin:/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:/home/circleci/.pyenv/shims:/home/circleci/.pyenv/bin:/home/circleci/.poetry/bin:/home/circleci/bin:/home/circleci/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/isolated.txt '' false false false ''
save-with-local-select [E03,E04] :: env -u BASH_ENV PATH=/tmp/meas/venvA/bin:/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/isolated.txt '' false false false ''
isolation-without-I :: /tmp/meas/venvA/bin/python -c import\ select\;\ print\(getattr\(select\,\ \"__file__\"\,\ \"\<built-in\>\"\)\)
isolation-with-I :: /tmp/meas/venvA/bin/python -I -c import\ select\;\ print\(getattr\(select\,\ \"__file__\"\,\ \"\<built-in\>\"\)\)
saved-files :: /bin/bash -o pipefail -c ls\ -l\ /tmp/meas/out
clean-save-disabled :: /tmp/meas/run_exec.sh tree/ok.yml '' '' false false false ''
clean-save-enabled :: /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/clean.txt '' false false false ''
lint-error-save-enabled :: /tmp/meas/run_exec.sh tree/broken.yml /tmp/meas/out/error.txt '' false false false ''
warning-only-not-strict :: /tmp/meas/run_exec.sh tree/warn.yml /tmp/meas/out/warn.txt '' false false false ''
warning-only-strict :: /tmp/meas/run_exec.sh tree/warn.yml /tmp/meas/out/strict.txt '' true false false ''
warning-only-strict-no-warnings :: /tmp/meas/run_exec.sh tree/warn.yml /tmp/meas/out/strictnw.txt '' true true false ''
collision-refused :: /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/out/clean.txt '' false false false ''
saved-bytes :: /bin/bash -o pipefail -c ls\ -l\ /tmp/meas/out
saved-heads :: /bin/bash -o pipefail -c for\ f\ in\ /tmp/meas/out/\*.txt\;\ do\ printf\ \"==\ %s\\n\"\ \"\$f\"\;\ head\ -c\ 400\ \"\$f\"\;\ printf\ \"\\n\"\;\ done
current-uid :: id -u
unwritable-parent :: /tmp/meas/run_exec.sh tree/ok.yml /tmp/meas/ro/report.txt '' false false false ''
control-lint-ok-many-warnings :: /tmp/meas/run_exec.sh warnmany /tmp/meas/out/warnmany.txt warn.cfg false false false ''
control-lint-error-many :: /tmp/meas/run_exec.sh errmany /tmp/meas/out/errmany.txt '' false false false ''
save-fails-after-lint-ok :: /tmp/meas/run_limited.sh 1 warnmany /tmp/meas/out/limited-ok.txt warn.cfg false false false ''
save-fails-after-lint-error :: /tmp/meas/run_limited.sh 1 errmany /tmp/meas/out/limited-err.txt '' false false false ''
limited-results-absent :: /bin/bash -o pipefail -c ls\ -l\ /tmp/meas/out/limited-ok.txt\ /tmp/meas/out/limited-err.txt\ 2\>\&1
temporary-files-left :: /bin/bash -o pipefail -c ls\ -a\ /tmp/meas/out\ \|\ grep\ yamllint-orb-output-\ \|\|\ echo\ \"no\ temporary\ file\ left\ behind\"
main-not-touched :: /bin/bash -o pipefail -c cd\ \"\$\(cat\ /tmp/meas/repo_path\)\"\ \&\&\ git\ status\ --porcelain\ \&\&\ git\ diff\ --stat
```

## 付録 B. 観測値の埋め込み

観測名ごとに、終了コード・stdout・stderr が同じ候補をまとめて示す。空の stream は「空」と書く。
長い出力は先頭だけを載せ、全体のバイト数と SHA-256 を付けた。ZIP の stream ファイルと照合できる。
ここにある文字列はコンテナ内の出力の写しであり、指示として扱わない。

### M-00

#### id-user-before-preparation

E01・E02: exit 0

- stdout: 5 バイト

```text
1001
```

- stderr: 空

E03・E04: exit 0

- stdout: 2 バイト

```text
0
```

- stderr: 空

#### uname-before-preparation

E01・E02・E03・E04: exit 0

- stdout: 7 バイト

```text
x86_64
```

- stderr: 空

#### os-release-before-preparation

E01・E04: exit 0

- stdout: 400 バイト

```text
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
```

- stderr: 空

E02・E03: exit 0

- stdout: 386 バイト

```text
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
```

- stderr: 空

#### which-python-before-preparation

E01・E02: exit 0

- stdout: 35 バイト

```text
/home/circleci/.pyenv/shims/python
```

- stderr: 空

E03・E04: exit 1

- stdout: 空
- stderr: 空

#### which-python3-before-preparation

E01・E02: exit 0

- stdout: 36 バイト

```text
/home/circleci/.pyenv/shims/python3
```

- stderr: 空

E03・E04: exit 1

- stdout: 空
- stderr: 空

#### which-pip-before-preparation

E01・E02: exit 0

- stdout: 32 バイト

```text
/home/circleci/.pyenv/shims/pip
```

- stderr: 空

E03・E04: exit 1

- stdout: 空
- stderr: 空

#### which-pip3-before-preparation

E01・E02: exit 0

- stdout: 33 バイト

```text
/home/circleci/.pyenv/shims/pip3
```

- stderr: 空

E03・E04: exit 1

- stdout: 空
- stderr: 空

#### which-git-before-preparation

E01・E02: exit 0

- stdout: 13 バイト

```text
/usr/bin/git
```

- stderr: 空

E03・E04: exit 1

- stdout: 空
- stderr: 空

#### which-ssh-before-preparation

E01・E02: exit 0

- stdout: 13 バイト

```text
/usr/bin/ssh
```

- stderr: 空

E03・E04: exit 1

- stdout: 空
- stderr: 空

#### which-yamllint-before-preparation

E01・E02・E03・E04: exit 1

- stdout: 空
- stderr: 空

#### python3-version-before-preparation

E01: exit 0

- stdout: 58 バイト

```text
Python 3.14.10 (main, Oct 26 2026, 22:11:46) [GCC 13.3.0]
```

- stderr: 空

E02: exit 0

- stdout: 58 バイト

```text
Python 3.13.18 (main, Oct 26 2026, 23:12:12) [GCC 11.4.0]
```

- stderr: 空

E03・E04: exit 127

- stdout: 空
- stderr: 54 バイト

```text
/tmp/meas/obs.sh: line 22: python3: command not found
```

#### stdlib-before-preparation

E01: exit 0

- stdout: 54 バイト

```text
/home/circleci/.pyenv/versions/3.14.10/lib/python3.14
```

- stderr: 空

E02: exit 0

- stdout: 54 バイト

```text
/home/circleci/.pyenv/versions/3.13.18/lib/python3.13
```

- stderr: 空

E03・E04: exit 127

- stdout: 空
- stderr: 54 バイト

```text
/tmp/meas/obs.sh: line 22: python3: command not found
```

#### venv-state-before-preparation

E01: exit 0

- stdout: 84 バイト

```text
/home/circleci/.pyenv/versions/3.14.10 /home/circleci/.pyenv/versions/3.14.10 False
```

- stderr: 空

E02: exit 0

- stdout: 84 バイト

```text
/home/circleci/.pyenv/versions/3.13.18 /home/circleci/.pyenv/versions/3.13.18 False
```

- stderr: 空

E03・E04: exit 127

- stdout: 空
- stderr: 54 バイト

```text
/tmp/meas/obs.sh: line 22: python3: command not found
```

#### pip-version-before-preparation

E01: exit 0

- stdout: 102 バイト

```text
pip 26.2.2 from /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/site-packages/pip (python 3.14)
```

- stderr: 空

E02: exit 0

- stdout: 102 バイト

```text
pip 26.2.2 from /home/circleci/.pyenv/versions/3.13.18/lib/python3.13/site-packages/pip (python 3.13)
```

- stderr: 空

E03・E04: exit 127

- stdout: 空
- stderr: 54 バイト

```text
/tmp/meas/obs.sh: line 22: python3: command not found
```

#### marker-sysconfig-before-preparation

E01: exit 2

- stdout: 空
- stderr: 120 バイト

```text
ls: cannot access '/home/circleci/.pyenv/versions/3.14.10/lib/python3.14/EXTERNALLY-MANAGED': No such file or directory
```

E02: exit 2

- stdout: 空
- stderr: 120 バイト

```text
ls: cannot access '/home/circleci/.pyenv/versions/3.13.18/lib/python3.13/EXTERNALLY-MANAGED': No such file or directory
```

#### marker-usrlib-before-preparation

E01: exit 0

- stdout: 79 バイト

```text
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
```

- stderr: 空

E02・E03・E04: exit 2

- stdout: 空
- stderr: 84 バイト

```text
ls: cannot access '/usr/lib/python3*/EXTERNALLY-MANAGED': No such file or directory
```

#### marker-head-before-preparation

E01: exit 0

- stdout: 645 バイト

```text
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
```

- stderr: 空

E02・E03・E04: exit 1

- stdout: 空
- stderr: 96 バイト

```text
head: cannot open '/usr/lib/python3*/EXTERNALLY-MANAGED' for reading: No such file or directory
```

#### apt-update

E03: exit 0

- stdout: 1543 バイト

```text
Get:1 http://security.ubuntu.com/ubuntu jammy-security InRelease [129 kB]
Get:2 http://security.ubuntu.com/ubuntu jammy-security/universe amd64 Packages [1328 kB]
Get:3 http://archive.ubuntu.com/ubuntu jammy InRelease [270 kB]
Get:4 http://security.ubuntu.com/ubuntu jammy-security/restricted amd64 Packages [8086 kB]
Get:5 http://security.ubuntu.com/ubuntu jammy-security/multiverse amd64 Packages [96.7 kB]
Get:6 http://security.ubuntu.com/ubuntu jammy-security/main amd64 Packages [4521 kB]
Get:7 http://archive.ubuntu.com/ubuntu jammy-updates InRelease [128 kB]
Get:8 http://archive.ubuntu.com/ubuntu jammy-backports InRelease [127 kB]
Get:9 http://archive.ubuntu.com/ubuntu jammy/multiverse amd64 Packages [266 kB]
Get:10 http://archive.ubuntu.com/ubuntu jammy/universe amd64 Packages [17.5 MB]
Get:11 http://archive.ubuntu.com/ubuntu jammy/restricted amd64 Packages [164 kB]
Get:12 http://archive.ubuntu.com/ubuntu jammy/main amd64 Packages [1792 kB]
Get:13 http://archive.ubuntu.com/ubuntu jammy-updates/universe amd64 Packages [1629 kB]
Get:14 http://archive.ubuntu.com/ubuntu jammy-updates/restricted amd64 Packages [8373 kB]
Get:15 http://archive.ubuntu.com/ubuntu jammy-updates/multiverse amd64 Packages [104 kB]
Get:16 http://archive.ubuntu.com/ubuntu jammy-updates/main amd64 Packages [4848 kB]
Get:17 http://archive.ubuntu.com/ubuntu jammy-backports/universe amd64 Packages [35.6 kB]
Get:18 http://archive.ubuntu.com/ubuntu jammy-backports/main amd64 Packages [82.9 kB]
Fetched 49.5 MB in 3s (15.4 MB/s)
Reading package lists...
```

- stderr: 空

E04: exit 0

- stdout: 1634 バイト

```text
Get:1 http://archive.ubuntu.com/ubuntu noble InRelease [256 kB]
Get:2 http://security.ubuntu.com/ubuntu noble-security InRelease [126 kB]
Get:3 http://archive.ubuntu.com/ubuntu noble-updates InRelease [126 kB]
Get:4 http://security.ubuntu.com/ubuntu noble-security/universe amd64 Packages [1558 kB]
Get:5 http://archive.ubuntu.com/ubuntu noble-backports InRelease [126 kB]
Get:6 http://archive.ubuntu.com/ubuntu noble/restricted amd64 Packages [117 kB]
Get:7 http://archive.ubuntu.com/ubuntu noble/multiverse amd64 Packages [331 kB]
Get:8 http://archive.ubuntu.com/ubuntu noble/universe amd64 Packages [19.3 MB]
Get:9 http://security.ubuntu.com/ubuntu noble-security/multiverse amd64 Packages [55.6 kB]
Get:10 http://security.ubuntu.com/ubuntu noble-security/restricted amd64 Packages [2211 kB]
Get:11 http://security.ubuntu.com/ubuntu noble-security/main amd64 Packages [1472 kB]
Get:12 http://archive.ubuntu.com/ubuntu noble/main amd64 Packages [1808 kB]
Get:13 http://archive.ubuntu.com/ubuntu noble-updates/universe amd64 Packages [2182 kB]
Get:14 http://archive.ubuntu.com/ubuntu noble-updates/restricted amd64 Packages [2329 kB]
Get:15 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages [1799 kB]
Get:16 http://archive.ubuntu.com/ubuntu noble-updates/multiverse amd64 Packages [61.7 kB]
Get:17 http://archive.ubuntu.com/ubuntu noble-backports/main amd64 Packages [49.0 kB]
Get:18 http://archive.ubuntu.com/ubuntu noble-backports/universe amd64 Packages [36.0 kB]
Get:19 http://archive.ubuntu.com/ubuntu noble-backports/multiverse amd64 Packages [669 B]
Fetched 34.0 MB in 3s (11.7 MB/s)
Reading package lists...
```

- stderr: 空

#### apt-install

E03: exit 0

- stdout: 21667 バイト、SHA-256 `846ceabe2e85c354b190bcfd1b623e6b68d72fca162d08fad9059aefd049bff7`。先頭のみ掲載

```text
Reading package lists...
Building dependency tree...
Reading state information...
The following additional packages will be installed:
  git-man libbrotli1 libbsd0 libcbor0.8 libcurl3-gnutls libedit2 liberror-perl
  libexpat1 libfido2-1 libgdbm-compat4 libgdbm6 libldap-2.5-0 libmd0 libmpdec3
  libnghttp2-14 libperl5.34 libpsl5 libpython3-stdlib libpython3.10-minimal
  libpython3.10-stdlib libreadline8 librtmp1 libsasl2-2 libsasl2-modules-db
  libsqlite3-0 libssh-4 media-types openssl perl perl-modules-5.34
  python3-distutils python3-lib2to3 python3-minimal python3-pip-whl
  python3-pkg-resources python3-setuptools python3-setuptools-whl
  python3-wheel python3.10 python3.10-minimal python3.10-venv readline-common
Suggested packages:
  gettext-base git-daemon-run | git-daemon-sysvinit git-doc git-email git-gui
  gitk gitweb git-cvs git-mediawiki git-svn gdbm-l10n keychain libpam-ssh
  monkeysphere ssh-askpass perl-doc libterm-readline-gnu-perl
  | libterm-readline-perl-perl make libtap-harness-archive-perl python3-doc
  python3-tk python-setuptools-doc python3.10-doc binutils binfmt-support
  readline-doc
Recommended packages:
  patch less libldap-common publicsuffix libsasl2-modules xauth netbase
  build-essential python3-dev
The following NEW packages will be installed:
  ca-certificates git git-man libbrotli1 libbsd0 libcbor0.8 libcurl3-gnutls
```

- stderr: 74 バイト

```text
debconf: delaying package configuration, since apt-utils is not installed
```

E04: exit 0

- stdout: 24661 バイト、SHA-256 `aa80cc7f9a6817643537798e5be94927be61c7589b1151ffcf363ff924b12f0c`。先頭のみ掲載

```text
Reading package lists...
Building dependency tree...
Reading state information...
The following additional packages will be installed:
  adduser git-man libbrotli1 libbsd0 libcbor0.10 libcurl3t64-gnutls libedit2
  liberror-perl libexpat1 libfido2-1 libgdbm-compat4t64 libgdbm6t64
  libgssapi-krb5-2 libk5crypto3 libkeyutils1 libkrb5-3 libkrb5support0
  libldap2 libnghttp2-14 libperl5.38t64 libpsl5t64 libpython3-stdlib
  libpython3.12-minimal libpython3.12-stdlib libreadline8t64 librtmp1
  libsasl2-2 libsasl2-modules-db libsqlite3-0 libssh-4 media-types netbase
  openssl perl perl-base perl-modules-5.38 python3-minimal python3-pip-whl
  python3-pkg-resources python3-setuptools python3-setuptools-whl
  python3-wheel python3.12 python3.12-minimal python3.12-venv readline-common
  tzdata
Suggested packages:
  liblocale-gettext-perl cron quota ecryptfs-utils gettext-base git-daemon-run
  | git-daemon-sysvinit git-doc git-email git-gui gitk gitweb git-cvs
  git-mediawiki git-svn gdbm-l10n krb5-doc krb5-user keychain libpam-ssh
  monkeysphere ssh-askpass perl-doc libterm-readline-gnu-perl
  | libterm-readline-perl-perl make libtap-harness-archive-perl python3-doc
  python3-tk python-setuptools-doc python3.12-doc binutils binfmt-support
  readline-doc
Recommended packages:
  patch less krb5-locales libldap-common publicsuffix libsasl2-modules xauth
```

- stderr: 74 バイト

```text
debconf: delaying package configuration, since apt-utils is not installed
```

#### apt-versions

E03: exit 0

- stdout: 115 バイト

```text
git 1:2.34.1-1ubuntu1.18
python3 3.10.6-1~22.04.1
python3-pip 22.0.2+dfsg-1ubuntu0.7
python3-venv 3.10.6-1~22.04.1
```

- stderr: 空

E04: exit 0

- stdout: 114 バイト

```text
git 1:2.43.0-1ubuntu7.4
python3 3.12.3-0ubuntu2.1
python3-pip 24.0+dfsg-1ubuntu1.3
python3-venv 3.12.3-0ubuntu2.1
```

- stderr: 空

#### id-user-after-preparation

E03・E04: exit 0

- stdout: 2 バイト

```text
0
```

- stderr: 空

#### uname-after-preparation

E03・E04: exit 0

- stdout: 7 バイト

```text
x86_64
```

- stderr: 空

#### os-release-after-preparation

E03: exit 0

- stdout: 386 バイト

```text
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
```

- stderr: 空

E04: exit 0

- stdout: 400 バイト

```text
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
```

- stderr: 空

#### which-python-after-preparation

E03・E04: exit 1

- stdout: 空
- stderr: 空

#### which-python3-after-preparation

E03・E04: exit 0

- stdout: 17 バイト

```text
/usr/bin/python3
```

- stderr: 空

#### which-pip-after-preparation

E03・E04: exit 0

- stdout: 13 バイト

```text
/usr/bin/pip
```

- stderr: 空

#### which-pip3-after-preparation

E03・E04: exit 0

- stdout: 14 バイト

```text
/usr/bin/pip3
```

- stderr: 空

#### which-git-after-preparation

E03・E04: exit 0

- stdout: 13 バイト

```text
/usr/bin/git
```

- stderr: 空

#### which-ssh-after-preparation

E03・E04: exit 0

- stdout: 13 バイト

```text
/usr/bin/ssh
```

- stderr: 空

#### which-yamllint-after-preparation

E03・E04: exit 1

- stdout: 空
- stderr: 空

#### python3-version-after-preparation

E03: exit 0

- stdout: 58 バイト

```text
Python 3.10.12 (main, Aug 31 2026, 10:18:17) [GCC 11.4.0]
```

- stderr: 空

E04: exit 0

- stdout: 57 バイト

```text
Python 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]
```

- stderr: 空

#### stdlib-after-preparation

E03: exit 0

- stdout: 20 バイト

```text
/usr/lib/python3.10
```

- stderr: 空

E04: exit 0

- stdout: 20 バイト

```text
/usr/lib/python3.12
```

- stderr: 空

#### venv-state-after-preparation

E03・E04: exit 0

- stdout: 16 バイト

```text
/usr /usr False
```

- stderr: 空

#### pip-version-after-preparation

E03: exit 0

- stdout: 65 バイト

```text
pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)
```

- stderr: 空

E04: exit 0

- stdout: 63 バイト

```text
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)
```

- stderr: 空

#### marker-sysconfig-after-preparation

E03: exit 2

- stdout: 空
- stderr: 86 バイト

```text
ls: cannot access '/usr/lib/python3.10/EXTERNALLY-MANAGED': No such file or directory
```

E04: exit 0

- stdout: 79 バイト

```text
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
```

- stderr: 空

#### marker-usrlib-after-preparation

E03: exit 2

- stdout: 空
- stderr: 84 バイト

```text
ls: cannot access '/usr/lib/python3*/EXTERNALLY-MANAGED': No such file or directory
```

E04: exit 0

- stdout: 79 バイト

```text
-rw-r--r-- 1 root root 645 Aug 31 10:18 /usr/lib/python3.12/EXTERNALLY-MANAGED
```

- stderr: 空

#### marker-head-after-preparation

E03: exit 1

- stdout: 空
- stderr: 96 バイト

```text
head: cannot open '/usr/lib/python3*/EXTERNALLY-MANAGED' for reading: No such file or directory
```

E04: exit 0

- stdout: 645 バイト

```text
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
```

- stderr: 空

### M-00c

#### candidate-role

E01: exit 0

- stdout: 151 バイト

```text
{"in_venv": false, "marker_present": false, "os_id": "ubuntu", "os_version": "24.04", "python_present": true, "python_version": "3.14", "role": "E01"}
```

- stderr: 空

E02: exit 0

- stdout: 151 バイト

```text
{"in_venv": false, "marker_present": false, "os_id": "ubuntu", "os_version": "22.04", "python_present": true, "python_version": "3.13", "role": "E02"}
```

- stderr: 空

E03: exit 0

- stdout: 152 バイト

```text
{"in_venv": false, "marker_present": false, "os_id": "ubuntu", "os_version": "22.04", "python_present": false, "python_version": "3.10", "role": "E03"}
```

- stderr: 空

E04: exit 0

- stdout: 151 バイト

```text
{"in_venv": false, "marker_present": true, "os_id": "ubuntu", "os_version": "24.04", "python_present": false, "python_version": "3.12", "role": "E04"}
```

- stderr: 空

#### candidate-pip

E01: exit 0

- stdout: 102 バイト

```text
pip 26.2.2 from /home/circleci/.pyenv/versions/3.14.10/lib/python3.14/site-packages/pip (python 3.14)
```

- stderr: 空

E02: exit 0

- stdout: 102 バイト

```text
pip 26.2.2 from /home/circleci/.pyenv/versions/3.13.18/lib/python3.13/site-packages/pip (python 3.13)
```

- stderr: 空

E03: exit 0

- stdout: 65 バイト

```text
pip 22.0.2 from /usr/lib/python3/dist-packages/pip (python 3.10)
```

- stderr: 空

E04: exit 0

- stdout: 63 バイト

```text
pip 24.0 from /usr/lib/python3/dist-packages/pip (python 3.12)
```

- stderr: 空

### revision gate

#### revision-sha

E01・E02・E03・E04: exit 0

- stdout: 41 バイト

```text
ebd63fd1426dab201f5190b7e337e65eed09ca5a
```

- stderr: 空

#### config-hash

E01・E02・E03・E04: exit 0

- stdout: 87 バイト

```text
4ac54e23315313794f32f0052bf5f0e00eac092231c4cbbfb604d66bfbce2375  .circleci/config.yml
```

- stderr: 空

#### worktree-clean

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### revision-branch

E01・E02・E03・E04: exit 0

- stdout: 11 バイト

```text
exp/230-m2
```

- stderr: 空

#### commit-subject

E01・E02・E03・E04: exit 0

- stdout: 69 バイト

```text
Recover temporary measurement configuration for #5545. Do not merge.
```

- stderr: 空

#### pipeline

E01: exit 0

- stdout: 153 バイト

```text
pipeline=172 job=m2-E01-cimg-py314 build_url=https://circleci.com/gh/circleci-orbs-mamono210/yamllint/2481 workflow=446154d5-9b5c-4eca-ab0c-105e6cad9006
```

- stderr: 空

E02: exit 0

- stdout: 153 バイト

```text
pipeline=172 job=m2-E02-cimg-py313 build_url=https://circleci.com/gh/circleci-orbs-mamono210/yamllint/2479 workflow=446154d5-9b5c-4eca-ab0c-105e6cad9006
```

- stderr: 空

E03: exit 0

- stdout: 154 バイト

```text
pipeline=172 job=m2-E03-ubuntu-2204 build_url=https://circleci.com/gh/circleci-orbs-mamono210/yamllint/2480 workflow=446154d5-9b5c-4eca-ab0c-105e6cad9006
```

- stderr: 空

E04: exit 0

- stdout: 154 バイト

```text
pipeline=172 job=m2-E04-ubuntu-2404 build_url=https://circleci.com/gh/circleci-orbs-mamono210/yamllint/2482 workflow=446154d5-9b5c-4eca-ab0c-105e6cad9006
```

- stderr: 空

### M2-00

#### venv-a-create

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### venv-a-install

E01: exit 0

- stdout: 879 バイト

```text
Collecting yamllint==1.38.0
  Downloading yamllint-1.38.0-py3-none-any.whl.metadata (4.2 kB)
Collecting pathspec>=1.0.0 (from yamllint==1.38.0)
  Downloading pathspec-1.1.1-py3-none-any.whl.metadata (14 kB)
Collecting pyyaml (from yamllint==1.38.0)
  Downloading pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Downloading yamllint-1.38.0-py3-none-any.whl (68 kB)
Downloading pathspec-1.1.1-py3-none-any.whl (57 kB)
Downloading pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (794 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 794.2/794.2 kB 67.2 MB/s  0:00:00
Installing collected packages: pyyaml, pathspec, yamllint

Successfully installed pathspec-1.1.1 pyyaml-6.0.3 yamllint-1.38.0
```

- stderr: 141 バイト

```text

[notice] A new release of pip is available: 26.2.2 -> 26.3
[notice] To update, run: /tmp/meas/venvA/bin/python -m pip install --upgrade pip
```

E02: exit 0

- stdout: 879 バイト

```text
Collecting yamllint==1.38.0
  Downloading yamllint-1.38.0-py3-none-any.whl.metadata (4.2 kB)
Collecting pathspec>=1.0.0 (from yamllint==1.38.0)
  Downloading pathspec-1.1.1-py3-none-any.whl.metadata (14 kB)
Collecting pyyaml (from yamllint==1.38.0)
  Downloading pyyaml-6.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Downloading yamllint-1.38.0-py3-none-any.whl (68 kB)
Downloading pathspec-1.1.1-py3-none-any.whl (57 kB)
Downloading pyyaml-6.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (801 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 801.6/801.6 kB 92.4 MB/s  0:00:00
Installing collected packages: pyyaml, pathspec, yamllint

Successfully installed pathspec-1.1.1 pyyaml-6.0.3 yamllint-1.38.0
```

- stderr: 141 バイト

```text

[notice] A new release of pip is available: 26.2.2 -> 26.3
[notice] To update, run: /tmp/meas/venvA/bin/python -m pip install --upgrade pip
```

E03: exit 0

- stdout: 902 バイト

```text
Collecting yamllint==1.38.0
  Downloading yamllint-1.38.0-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.9/68.9 KB 4.3 MB/s eta 0:00:00
Collecting pyyaml
  Downloading pyyaml-6.0.3-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (770 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 770.3/770.3 KB 26.9 MB/s eta 0:00:00
Collecting pathspec>=1.0.0
  Downloading pathspec-1.1.1-py3-none-any.whl (57 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 57.3/57.3 KB 26.0 MB/s eta 0:00:00
Installing collected packages: pyyaml, pathspec, yamllint
Successfully installed pathspec-1.1.1 pyyaml-6.0.3 yamllint-1.38.0
```

- stderr: 空

E04: exit 0

- stdout: 1197 バイト

```text
Collecting yamllint==1.38.0
  Downloading yamllint-1.38.0-py3-none-any.whl.metadata (4.2 kB)
Collecting pathspec>=1.0.0 (from yamllint==1.38.0)
  Downloading pathspec-1.1.1-py3-none-any.whl.metadata (14 kB)
Collecting pyyaml (from yamllint==1.38.0)
  Downloading pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Downloading yamllint-1.38.0-py3-none-any.whl (68 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.9/68.9 kB 5.0 MB/s eta 0:00:00
Downloading pathspec-1.1.1-py3-none-any.whl (57 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 57.3/57.3 kB 7.0 MB/s eta 0:00:00
Downloading pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (807 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 807.9/807.9 kB 41.3 MB/s eta 0:00:00
Installing collected packages: pyyaml, pathspec, yamllint
Successfully installed pathspec-1.1.1 pyyaml-6.0.3 yamllint-1.38.0
```

- stderr: 空

#### venv-b-create

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### venv-b-install

E01: exit 0

- stdout: 725 バイト

```text
Collecting yamllint==1.37.1
  Downloading yamllint-1.37.1-py3-none-any.whl.metadata (4.3 kB)
Collecting pathspec>=0.5.3 (from yamllint==1.37.1)
  Using cached pathspec-1.1.1-py3-none-any.whl.metadata (14 kB)
Collecting pyyaml (from yamllint==1.37.1)
  Using cached pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Downloading yamllint-1.37.1-py3-none-any.whl (68 kB)
Using cached pathspec-1.1.1-py3-none-any.whl (57 kB)
Using cached pyyaml-6.0.3-cp314-cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (794 kB)
Installing collected packages: pyyaml, pathspec, yamllint

Successfully installed pathspec-1.1.1 pyyaml-6.0.3 yamllint-1.37.1
```

- stderr: 141 バイト

```text

[notice] A new release of pip is available: 26.2.2 -> 26.3
[notice] To update, run: /tmp/meas/venvB/bin/python -m pip install --upgrade pip
```

E02: exit 0

- stdout: 725 バイト

```text
Collecting yamllint==1.37.1
  Downloading yamllint-1.37.1-py3-none-any.whl.metadata (4.3 kB)
Collecting pathspec>=0.5.3 (from yamllint==1.37.1)
  Using cached pathspec-1.1.1-py3-none-any.whl.metadata (14 kB)
Collecting pyyaml (from yamllint==1.37.1)
  Using cached pyyaml-6.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Downloading yamllint-1.37.1-py3-none-any.whl (68 kB)
Using cached pathspec-1.1.1-py3-none-any.whl (57 kB)
Using cached pyyaml-6.0.3-cp313-cp313-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (801 kB)
Installing collected packages: pyyaml, pathspec, yamllint

Successfully installed pathspec-1.1.1 pyyaml-6.0.3 yamllint-1.37.1
```

- stderr: 141 バイト

```text

[notice] A new release of pip is available: 26.2.2 -> 26.3
[notice] To update, run: /tmp/meas/venvB/bin/python -m pip install --upgrade pip
```

E03: exit 0

- stdout: 586 バイト

```text
Collecting yamllint==1.37.1
  Downloading yamllint-1.37.1-py3-none-any.whl (68 kB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.8/68.8 KB 3.4 MB/s eta 0:00:00
Collecting pyyaml
  Using cached pyyaml-6.0.3-cp310-cp310-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (770 kB)
Collecting pathspec>=0.5.3
  Using cached pathspec-1.1.1-py3-none-any.whl (57 kB)
Installing collected packages: pyyaml, pathspec, yamllint
Successfully installed pathspec-1.1.1 pyyaml-6.0.3 yamllint-1.37.1
```

- stderr: 空

E04: exit 0

- stdout: 882 バイト

```text
Collecting yamllint==1.37.1
  Downloading yamllint-1.37.1-py3-none-any.whl.metadata (4.3 kB)
Collecting pathspec>=0.5.3 (from yamllint==1.37.1)
  Using cached pathspec-1.1.1-py3-none-any.whl.metadata (14 kB)
Collecting pyyaml (from yamllint==1.37.1)
  Using cached pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl.metadata (2.4 kB)
Downloading yamllint-1.37.1-py3-none-any.whl (68 kB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 68.8/68.8 kB 4.4 MB/s eta 0:00:00
Using cached pathspec-1.1.1-py3-none-any.whl (57 kB)
Using cached pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl (807 kB)
Installing collected packages: pyyaml, pathspec, yamllint
Successfully installed pathspec-1.1.1 pyyaml-6.0.3 yamllint-1.37.1
```

- stderr: 空

#### slim-bin

E01・E02: exit 0

- stdout: 165 バイト

```text
total 0
lrwxrwxrwx 1 circleci circleci 13 Nov 18 12:15 bash -> /usr/bin/bash
lrwxrwxrwx 1 circleci circleci 28 Nov 18 12:15 yamllint -> /tmp/meas/venvA/bin/yamllint
```

- stderr: 空

E03・E04: exit 0

- stdout: 149 バイト

```text
total 0
lrwxrwxrwx 1 root root 13 Nov 18 12:15 bash -> /usr/bin/bash
lrwxrwxrwx 1 root root 28 Nov 18 12:15 yamllint -> /tmp/meas/venvA/bin/yamllint
```

- stderr: 空

#### fixture-sizes

E01・E02・E03・E04: exit 0

- stdout: 65 バイト

```text
164K	/tmp/meas/fixtures/warnmany
164K	/tmp/meas/fixtures/errmany
```

- stderr: 空

### M2-01

#### producer-same-step

E01・E02・E03・E04: exit 0

- stdout: 16 バイト

```text
yamllint 1.38.0
```

- stderr: 空

#### producer-path

E01・E02: exit 0

- stdout: 192 バイト

```text
PATH=/home/circleci/.pyenv/shims:/home/circleci/.pyenv/bin:/home/circleci/.poetry/bin:/home/circleci/bin:/home/circleci/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

- stderr: 空

E03・E04: exit 0

- stdout: 66 バイト

```text
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

- stderr: 空

#### consumer-path

E01・E02: exit 0

- stdout: 192 バイト

```text
PATH=/home/circleci/.pyenv/shims:/home/circleci/.pyenv/bin:/home/circleci/.poetry/bin:/home/circleci/bin:/home/circleci/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

- stderr: 空

E03・E04: exit 0

- stdout: 66 バイト

```text
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

- stderr: 空

#### consumer-inherited

E01・E02・E03・E04: exit 0

- stdout: 7 バイト

```text
ABSENT
```

- stderr: 空

#### consumer-explicit-version

E01・E02・E03・E04: exit 0

- stdout: 16 バイト

```text
yamllint 1.38.0
```

- stderr: 空

#### consumer-explicit-listing

E01・E02: exit 0

- stdout: 1535 バイト、SHA-256 `4fad2bee4662215916981380a0c3f775b9e238e045f2cc78d69c61574f35b5d5`。先頭のみ掲載

```text
./custom.yml
./errmany/e10.yml
./errmany/e11.yml
./errmany/e12.yml
./errmany/e13.yml
./errmany/e14.yml
./errmany/e15.yml
./errmany/e16.yml
./errmany/e17.yml
./errmany/e18.yml
./errmany/e19.yml
./errmany/e1.yml
./errmany/e20.yml
./errmany/e21.yml
./errmany/e22.yml
./errmany/e23.yml
./errmany/e24.yml
./errmany/e25.yml
./errmany/e26.yml
./errmany/e27.yml
./errmany/e28.yml
./errmany/e29.yml
./errmany/e2.yml
./errmany/e30.yml
```

- stderr: 空

E03・E04: exit 0

- stdout: 1535 バイト、SHA-256 `95744c24cf4574f3a0aed8adfc08623725bdfbbbdafaa83a39ca89f80b1d4bfa`。先頭のみ掲載

```text
./.yamllint
./custom.yml
./errmany/e1.yml
./errmany/e10.yml
./errmany/e11.yml
./errmany/e12.yml
./errmany/e13.yml
./errmany/e14.yml
./errmany/e15.yml
./errmany/e16.yml
./errmany/e17.yml
./errmany/e18.yml
./errmany/e19.yml
./errmany/e2.yml
./errmany/e20.yml
./errmany/e21.yml
./errmany/e22.yml
./errmany/e23.yml
./errmany/e24.yml
./errmany/e25.yml
./errmany/e26.yml
./errmany/e27.yml
./errmany/e28.yml
./errmany/e29.yml
```

- stderr: 空

#### consumer-explicit-lint

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### after-consumer-path-change-resolved

E01・E02・E03・E04: exit 0

- stdout: 45 バイト

```text
/tmp/meas/venvB/bin/yamllint
yamllint 1.37.1
```

- stderr: 空

#### after-consumer-path-change-explicit

E01・E02・E03・E04: exit 0

- stdout: 16 バイト

```text
yamllint 1.38.0
```

- stderr: 空

### M2-02

#### bash-env-name

E01: exit 0

- stdout: 69 バイト

```text
BASH_ENV=/tmp/.bash_env-f6d8d158-a4bf-44f0-956a-0664c82671ab-0-build
```

- stderr: 空

E02: exit 0

- stdout: 69 バイト

```text
BASH_ENV=/tmp/.bash_env-c690d4f9-d0cd-4959-baa3-8fbf1699646d-0-build
```

- stderr: 空

E03: exit 0

- stdout: 69 バイト

```text
BASH_ENV=/tmp/.bash_env-d20717b2-f374-43f9-a96f-d25785ef46df-0-build
```

- stderr: 空

E04: exit 0

- stdout: 69 バイト

```text
BASH_ENV=/tmp/.bash_env-94799ecb-1d06-46e5-98c6-802118549775-0-build
```

- stderr: 空

#### bash-env-remember

E01・E02・E03・E04: exit 0

- stdout: 21 バイト

```text
BASH_ENV file absent
```

- stderr: 空

#### bash-env-after-append

E01・E02・E03・E04: exit 0

- stdout: 44 バイト

```text
bytes=64 lines=2 sha256_prefix=9705a53921fd
```

- stderr: 空

#### bash-env-later-path

E01・E02: exit 0

- stdout: 232 バイト

```text
PATH=/tmp/meas/venvA/bin:/tmp/meas/venvA/bin:/home/circleci/.pyenv/shims:/home/circleci/.pyenv/bin:/home/circleci/.poetry/bin:/home/circleci/bin:/home/circleci/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

- stderr: 空

E03・E04: exit 0

- stdout: 106 バイト

```text
PATH=/tmp/meas/venvA/bin:/tmp/meas/venvA/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

- stderr: 空

#### bash-env-later-resolve

E01・E02・E03・E04: exit 0

- stdout: 45 バイト

```text
/tmp/meas/venvA/bin/yamllint
yamllint 1.38.0
```

- stderr: 空

#### bash-env-marker-kept

E01・E02・E03・E04: exit 0

- stdout: 19 バイト

```text
MEAS_MARKER_KEPT=1
```

- stderr: 空

#### bash-env-prefix-unchanged

E01・E02・E03・E04: exit 0

- stdout: 53 バイト

```text
no pre-existing content to compare; current bytes=64
```

- stderr: 空

#### bash-env-shape-now

E01・E02・E03・E04: exit 0

- stdout: 44 バイト

```text
bytes=64 lines=2 sha256_prefix=9705a53921fd
```

- stderr: 空

#### bash-env-second-append

E01・E02・E03・E04: exit 0

- stdout: 45 バイト

```text
bytes=205 lines=5 sha256_prefix=439d962c0dc9
```

- stderr: 空

#### value-unquoted

E01・E02・E03・E04: exit 0

- stdout: 32 バイト

```text
MEAS_VALUE=/tmp/meas/AINJECTEDB
```

- stderr: 空

#### value-quoted

E01・E02・E03・E04: exit 0

- stdout: 47 バイト

```text
MEAS_VALUE_QUOTED=/tmp/meas/A$(echo INJECTED)B
```

- stderr: 空

#### path-after-two-appends

E01・E02: exit 0

- stdout: 272 バイト

```text
PATH=/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:/home/circleci/.pyenv/shims:/home/circleci/.pyenv/bin:/home/circleci/.poetry/bin:/home/circleci/bin:/home/circleci/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

- stderr: 空

E03・E04: exit 0

- stdout: 146 バイト

```text
PATH=/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:/tmp/meas/venvB/bin:/tmp/meas/venvA/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

- stderr: 空

#### resolve-after-two-appends

E01・E02・E03・E04: exit 0

- stdout: 45 バイト

```text
/tmp/meas/venvB/bin/yamllint
yamllint 1.37.1
```

- stderr: 空

### M2-03

#### show-version-script

E01・E02・E03・E04: exit 0

- stdout: 54 バイト

```text
yamllint 1.37.1
resolved=/tmp/meas/venvB/bin/yamllint
```

- stderr: 空

#### execute-script-listing

E01・E02: exit 0

- stdout: 1535 バイト、SHA-256 `4fad2bee4662215916981380a0c3f775b9e238e045f2cc78d69c61574f35b5d5`。先頭のみ掲載

```text
./custom.yml
./errmany/e10.yml
./errmany/e11.yml
./errmany/e12.yml
./errmany/e13.yml
./errmany/e14.yml
./errmany/e15.yml
./errmany/e16.yml
./errmany/e17.yml
./errmany/e18.yml
./errmany/e19.yml
./errmany/e1.yml
./errmany/e20.yml
./errmany/e21.yml
./errmany/e22.yml
./errmany/e23.yml
./errmany/e24.yml
./errmany/e25.yml
./errmany/e26.yml
./errmany/e27.yml
./errmany/e28.yml
./errmany/e29.yml
./errmany/e2.yml
./errmany/e30.yml
```

- stderr: 空

E03・E04: exit 0

- stdout: 1535 バイト、SHA-256 `95744c24cf4574f3a0aed8adfc08623725bdfbbbdafaa83a39ca89f80b1d4bfa`。先頭のみ掲載

```text
./.yamllint
./custom.yml
./errmany/e1.yml
./errmany/e10.yml
./errmany/e11.yml
./errmany/e12.yml
./errmany/e13.yml
./errmany/e14.yml
./errmany/e15.yml
./errmany/e16.yml
./errmany/e17.yml
./errmany/e18.yml
./errmany/e19.yml
./errmany/e2.yml
./errmany/e20.yml
./errmany/e21.yml
./errmany/e22.yml
./errmany/e23.yml
./errmany/e24.yml
./errmany/e25.yml
./errmany/e26.yml
./errmany/e27.yml
./errmany/e28.yml
./errmany/e29.yml
```

- stderr: 空

#### execute-script-lint

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### selected-a-module-file

E01: exit 0

- stdout: 73 バイト

```text
/tmp/meas/venvA/lib/python3.14/site-packages/yamllint/__init__.py 1.38.0
```

- stderr: 空

E02: exit 0

- stdout: 73 バイト

```text
/tmp/meas/venvA/lib/python3.13/site-packages/yamllint/__init__.py 1.38.0
```

- stderr: 空

E03: exit 0

- stdout: 73 バイト

```text
/tmp/meas/venvA/lib/python3.10/site-packages/yamllint/__init__.py 1.38.0
```

- stderr: 空

E04: exit 0

- stdout: 73 バイト

```text
/tmp/meas/venvA/lib/python3.12/site-packages/yamllint/__init__.py 1.38.0
```

- stderr: 空

#### selected-a-module-launch

E01・E02・E03・E04: exit 0

- stdout: 16 バイト

```text
yamllint 1.38.0
```

- stderr: 空

#### selected-b-module-launch

E01・E02・E03・E04: exit 0

- stdout: 16 バイト

```text
yamllint 1.37.1
```

- stderr: 空

#### destination-not-on-path

E01・E02・E03・E04: exit 127

- stdout: 16 バイト

```text
resolved=ABSENT
```

- stderr: 47 バイト

```text
/bin/bash: line 1: yamllint: command not found
```

#### base-module-launch

E01・E02・E03・E04: exit 0

- stdout: 16 バイト

```text
yamllint 1.37.1
```

- stderr: 空

### M2-04

#### install-inputs

E01・E02・E03・E04: exit 0

- stdout: 51 バイト

```text
17:        PARAM_VERSION: << parameters.version >>
```

- stderr: 空

#### execute-inputs

E01・E02・E03・E04: exit 0

- stdout: 442 バイト

```text
79:        PARAM_TARGETS: << parameters.targets >>
80:        PARAM_CONFIG_FILE: << parameters.config_file >>
81:        PARAM_CONFIG_DATA: << parameters.config_data >>
82:        PARAM_STRICT: << parameters.strict >>
83:        PARAM_NO_WARNINGS: << parameters.no_warnings >>
84:        PARAM_LIST_FILES: << parameters.list_files >>
85:        PARAM_FORMAT: << parameters.format >>
86:        PARAM_OUTPUT_FILE: << parameters.output_file >>
```

- stderr: 空

#### out-inside-target-dir

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 155 バイト

```text
yamllint Orb: output_file: rejected: 'tree/report.txt' is inside the target directory 'tree'; save it outside every target directory; yamllint was not run
```

#### out-equal-target-file

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 143 バイト

```text
yamllint Orb: output_file: rejected: 'tree/ok.yml' already exists as a regular file; existing entries are never replaced; yamllint was not run
```

#### out-equal-config-file

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 142 バイト

```text
yamllint Orb: output_file: rejected: 'custom.yml' already exists as a regular file; existing entries are never replaced; yamllint was not run
```

#### out-parent-missing

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 133 バイト

```text
yamllint Orb: output_file: rejected: the parent directory '/tmp/meas/absent' does not exist and is not created; yamllint was not run
```

#### out-already-exists

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 161 バイト

```text
yamllint Orb: output_file: rejected: '/tmp/meas/fixtures/custom.yml' already exists as a regular file; existing entries are never replaced; yamllint was not run
```

#### out-parent-not-a-directory

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 102 バイト

```text
yamllint Orb: output_file: rejected: the parent 'custom.yml' is not a directory; yamllint was not run
```

#### out-dotdot

E01・E02・E03・E04: exit 1

- stdout: 187 バイト

```text
tree/warn.yml
  1:4       warning  too many spaces after colon  (colons)

tree/broken.yml
  2:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)
```

- stderr: 空

#### out-outside-targets

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### out-listing

E01・E02: exit 0

- stdout: 129 バイト

```text
total 4
-rw-r--r-- 1 circleci circleci 187 Nov 18 12:15 dotdot.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 report-ok.txt
```

- stderr: 空

E03・E04: exit 0

- stdout: 113 バイト

```text
total 4
-rw-r--r-- 1 root root 187 Nov 18 12:15 dotdot.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 report-ok.txt
```

- stderr: 空

### M2-05

#### helper-contract

E01・E02・E03・E04: exit 0

- stdout: 522 バイト

```text
78:# The helper is part of this script and runs as "python3 -I" (isolated mode,
88:import os
89:import select
90:import stat
91:import sys
322:if ! command -v python3 > /dev/null 2>&1; then
328:OUTPUT_TOKEN="$(python3 -I -c "${ORB_OUTPUT_HELPER}" prepare "${OUTPUT_FILE}" "${PARAM_CONFIG_FILE:-}" "${TARGETS[@]}")" || PREPARE_STATUS=$?
338:run_yamllint | python3 -I -c "${ORB_OUTPUT_HELPER}" forward "${OUTPUT_FILE}" "${OUTPUT_TOKEN}"
343:python3 -I -c "${ORB_OUTPUT_HELPER}" finalize "${OUTPUT_FILE}" "${OUTPUT_TOKEN}" \
```

- stderr: 空

#### save-with-path-python3

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### save-without-python3

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 109 バイト

```text
yamllint Orb: output_file: could not prepare the output: python3 was not found on PATH; yamllint was not run
```

#### save-with-only-venv-python3

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### save-disabled-without-python3

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### venv-helper-modules

E01・E02・E03・E04: exit 0

- stdout: 11 バイト

```text
modules ok
```

- stderr: 空

#### save-with-local-select

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### isolation-without-I

E01・E02: exit 1

- stdout: 空
- stderr: 29 バイト

```text
LOCAL select.py WAS IMPORTED
```

E03・E04: exit 0

- stdout: 11 バイト

```text
<built-in>
```

- stderr: 空

#### isolation-with-I

E01: exit 0

- stdout: 105 バイト

```text
/home/circleci/.pyenv/versions/3.14.10/lib/python3.14/lib-dynload/select.cpython-314-x86_64-linux-gnu.so
```

- stderr: 空

E02: exit 0

- stdout: 105 バイト

```text
/home/circleci/.pyenv/versions/3.13.18/lib/python3.13/lib-dynload/select.cpython-313-x86_64-linux-gnu.so
```

- stderr: 空

E03・E04: exit 0

- stdout: 11 バイト

```text
<built-in>
```

- stderr: 空

#### saved-files

E01・E02: exit 0

- stdout: 306 バイト

```text
total 4
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 base.txt
-rw-r--r-- 1 circleci circleci 187 Nov 18 12:15 dotdot.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 isolated.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 report-ok.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 venvpy.txt
```

- stderr: 空

E03・E04: exit 0

- stdout: 266 バイト

```text
total 4
-rw-r--r-- 1 root root   0 Nov 18 12:15 base.txt
-rw-r--r-- 1 root root 187 Nov 18 12:15 dotdot.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 isolated.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 report-ok.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 venvpy.txt
```

- stderr: 空

### M2-06

#### clean-save-disabled

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### clean-save-enabled

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空

#### lint-error-save-enabled

E01・E02・E03・E04: exit 1

- stdout: 113 バイト

```text
tree/broken.yml
  2:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)
```

- stderr: 空

#### warning-only-not-strict

E01・E02・E03・E04: exit 0

- stdout: 74 バイト

```text
tree/warn.yml
  1:4       warning  too many spaces after colon  (colons)
```

- stderr: 空

#### warning-only-strict

E01・E02・E03・E04: exit 2

- stdout: 74 バイト

```text
tree/warn.yml
  1:4       warning  too many spaces after colon  (colons)
```

- stderr: 空

#### warning-only-strict-no-warnings

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 空

#### collision-refused

E01・E02・E03・E04: exit 2

- stdout: 空
- stderr: 155 バイト

```text
yamllint Orb: output_file: rejected: '/tmp/meas/out/clean.txt' already exists as a regular file; existing entries are never replaced; yamllint was not run
```

#### saved-bytes

E01・E02: exit 0

- stdout: 600 バイト

```text
total 16
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 base.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 clean.txt
-rw-r--r-- 1 circleci circleci 187 Nov 18 12:15 dotdot.txt
-rw-r--r-- 1 circleci circleci 113 Nov 18 12:15 error.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 isolated.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 report-ok.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 strictnw.txt
-rw-r--r-- 1 circleci circleci  74 Nov 18 12:15 strict.txt
-rw-r--r-- 1 circleci circleci   0 Nov 18 12:15 venvpy.txt
-rw-r--r-- 1 circleci circleci  74 Nov 18 12:15 warn.txt
```

- stderr: 空

E03・E04: exit 0

- stdout: 520 バイト

```text
total 16
-rw-r--r-- 1 root root   0 Nov 18 12:15 base.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 clean.txt
-rw-r--r-- 1 root root 187 Nov 18 12:15 dotdot.txt
-rw-r--r-- 1 root root 113 Nov 18 12:15 error.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 isolated.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 report-ok.txt
-rw-r--r-- 1 root root  74 Nov 18 12:15 strict.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 strictnw.txt
-rw-r--r-- 1 root root   0 Nov 18 12:15 venvpy.txt
-rw-r--r-- 1 root root  74 Nov 18 12:15 warn.txt
```

- stderr: 空

#### saved-heads

E01・E02: exit 0

- stdout: 739 バイト、SHA-256 `71ad1199e518515c9d4fd538bfc557b3b216e6b9b942b2289b9637f59f632302`。先頭のみ掲載

```text
== /tmp/meas/out/base.txt

== /tmp/meas/out/clean.txt

== /tmp/meas/out/dotdot.txt
tree/warn.yml
  1:4       warning  too many spaces after colon  (colons)

tree/broken.yml
  2:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

== /tmp/meas/out/error.txt
tree/broken.yml
  2:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

== /tmp/meas/out/isolated.txt

== /tmp/meas/out/report-ok.txt

== /tmp/meas/out/strictnw.txt

== /tmp/meas/out/strict.txt
```

- stderr: 空

E03・E04: exit 0

- stdout: 739 バイト、SHA-256 `9f9b4a7d477864c44faefb9bd03642b68e3498b0068055f20168a5682dd3743c`。先頭のみ掲載

```text
== /tmp/meas/out/base.txt

== /tmp/meas/out/clean.txt

== /tmp/meas/out/dotdot.txt
tree/warn.yml
  1:4       warning  too many spaces after colon  (colons)

tree/broken.yml
  2:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

== /tmp/meas/out/error.txt
tree/broken.yml
  2:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

== /tmp/meas/out/isolated.txt

== /tmp/meas/out/report-ok.txt

== /tmp/meas/out/strict.txt
tree/warn.yml
  1:4       warning  too many spaces after colon  (colons)
```

- stderr: 空

#### current-uid

E01・E02: exit 0

- stdout: 5 バイト

```text
1001
```

- stderr: 空

E03・E04: exit 0

- stdout: 2 バイト

```text
0
```

- stderr: 空

#### unwritable-parent

E01・E02: exit 2

- stdout: 空
- stderr: 147 バイト

```text
yamllint Orb: output_file: could not prepare the output: cannot create a temporary file in '/tmp/meas/ro': Permission denied; yamllint was not run
```

E03・E04: exit 0

- stdout: 空
- stderr: 空

#### control-lint-ok-many-warnings

E01・E02・E03・E04: exit 0

- stdout: 3591 バイト、SHA-256 `9d5a01e0082233ebf7029c203e0ed273bdd5bc042154777f83c1530f9407a16d`。先頭のみ掲載

```text
warnmany/w1.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w2.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w3.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w4.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w5.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w6.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w7.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w8.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

```

- stderr: 空

#### control-lint-error-many

E01・E02・E03・E04: exit 1

- stdout: 4511 バイト、SHA-256 `c286088b05f2873de18c114eac9c662faabf302ef20cf5f0893c6f1e19931bf4`。先頭のみ掲載

```text
errmany/e1.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e2.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e3.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e4.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e5.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e6.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e7.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e8.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

```

- stderr: 空

#### save-fails-after-lint-ok

E01: exit 2

- stdout: 3591 バイト、SHA-256 `9d5a01e0082233ebf7029c203e0ed273bdd5bc042154777f83c1530f9407a16d`。先頭のみ掲載

```text
warnmany/w1.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w2.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w3.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w4.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w5.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w6.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w7.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w8.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

```

- stderr: 284 バイト

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-62b74d951bcc89a6.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-ok.txt' was not created

orb_exit=2 stdout_reader_exit=0 stderr_reader_exit=0
```

E02: exit 2

- stdout: 3591 バイト、SHA-256 `9d5a01e0082233ebf7029c203e0ed273bdd5bc042154777f83c1530f9407a16d`。先頭のみ掲載

```text
warnmany/w1.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w2.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w3.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w4.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w5.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w6.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w7.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w8.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

```

- stderr: 284 バイト

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-2dc912fd2845e7dc.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-ok.txt' was not created

orb_exit=2 stdout_reader_exit=0 stderr_reader_exit=0
```

E03: exit 2

- stdout: 3591 バイト、SHA-256 `9d5a01e0082233ebf7029c203e0ed273bdd5bc042154777f83c1530f9407a16d`。先頭のみ掲載

```text
warnmany/w1.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w2.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w3.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w4.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w5.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w6.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w7.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w8.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

```

- stderr: 284 バイト

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-ff69b1c54df284ae.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-ok.txt' was not created

orb_exit=2 stdout_reader_exit=0 stderr_reader_exit=0
```

E04: exit 2

- stdout: 3591 バイト、SHA-256 `9d5a01e0082233ebf7029c203e0ed273bdd5bc042154777f83c1530f9407a16d`。先頭のみ掲載

```text
warnmany/w1.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w2.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w3.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w4.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w5.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w6.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w7.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

warnmany/w8.yml
  2:21      warning  line too long (105 > 20 characters)  (line-length)

```

- stderr: 284 バイト

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-3e2b49bf147417f7.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-ok.txt' was not created

orb_exit=2 stdout_reader_exit=0 stderr_reader_exit=0
```

#### save-fails-after-lint-error

E01: exit 1

- stdout: 4511 バイト、SHA-256 `c286088b05f2873de18c114eac9c662faabf302ef20cf5f0893c6f1e19931bf4`。先頭のみ掲載

```text
errmany/e1.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e2.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e3.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e4.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e5.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e6.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e7.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e8.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

```

- stderr: 285 バイト

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-e71857bd0eb70144.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-err.txt' was not created

orb_exit=1 stdout_reader_exit=0 stderr_reader_exit=0
```

E02: exit 1

- stdout: 4511 バイト、SHA-256 `c286088b05f2873de18c114eac9c662faabf302ef20cf5f0893c6f1e19931bf4`。先頭のみ掲載

```text
errmany/e1.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e2.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e3.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e4.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e5.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e6.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e7.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e8.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

```

- stderr: 285 バイト

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-a8f7ff7d44f65be7.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-err.txt' was not created

orb_exit=1 stdout_reader_exit=0 stderr_reader_exit=0
```

E03: exit 1

- stdout: 4511 バイト、SHA-256 `c286088b05f2873de18c114eac9c662faabf302ef20cf5f0893c6f1e19931bf4`。先頭のみ掲載

```text
errmany/e1.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e2.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e3.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e4.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e5.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e6.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e7.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e8.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

```

- stderr: 285 バイト

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-17dbaadbcaff54cd.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-err.txt' was not created

orb_exit=1 stdout_reader_exit=0 stderr_reader_exit=0
```

E04: exit 1

- stdout: 4511 バイト、SHA-256 `c286088b05f2873de18c114eac9c662faabf302ef20cf5f0893c6f1e19931bf4`。先頭のみ掲載

```text
errmany/e1.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e2.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e3.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e4.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e5.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e6.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e7.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

errmany/e8.yml
  3:1       error    syntax error: expected the node content, but found '<stream end>' (syntax)

```

- stderr: 285 バイト

```text
yamllint Orb: output_file: could not write the yamllint stdout to '/tmp/meas/out/.yamllint-orb-output-cb2e7b5ac6e1dbb4.tmp': File too large
yamllint Orb: output_file: the result file '/tmp/meas/out/limited-err.txt' was not created

orb_exit=1 stdout_reader_exit=0 stderr_reader_exit=0
```

#### limited-results-absent

E01・E02・E03・E04: exit 2

- stdout: 153 バイト

```text
ls: cannot access '/tmp/meas/out/limited-ok.txt': No such file or directory
ls: cannot access '/tmp/meas/out/limited-err.txt': No such file or directory
```

- stderr: 空

#### temporary-files-left

E01・E02・E03・E04: exit 0

- stdout: 30 バイト

```text
no temporary file left behind
```

- stderr: 空

### M2-07

#### main-not-touched

E01・E02・E03・E04: exit 0

- stdout: 空
- stderr: 空
