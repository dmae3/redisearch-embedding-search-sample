# redisearch-embedding-search-sample

このリポジトリは、RediSearchを使用してベクトル検索（embedding search）を行うサンプルアプリケーションです。AirBnBのリスティングデータとそのテキスト埋め込みを使用して、類似のリスティングを検索する機能を提供します。

## 主な特徴

- RediSearchを使用したベクトル検索
- Hugging Faceのデータセット（MongoDB/airbnb_embeddings）の利用
- OpenAI API（text-embedding-3-small モデル）を使用したテキスト埋め込みの生成
- テキスト埋め込みを使用した類似性検索
- 価格範囲によるフィルタリング機能

## 必要条件

- Docker
- Docker Compose
- OpenAI API キー

## セットアップと使用方法

1. リポジトリのクローン:
   ```
   git clone https://github.com/dmae3/redisearch-embedding-search-sample.git
   cd redisearch-embedding-search-sample
   ```

2. OpenAI API キーの設定:
   ホストマシンで環境変数を設定します：
   ```
   export OPENAI_API_KEY=your_actual_api_key_here
   ```

3. Docker Composeを使用してビルドと起動:
   ```
   docker-compose up --build
   ```

   注: docker-compose.ymlファイルは環境変数 `OPENAI_API_KEY` を使用してAPIキーをコンテナに渡します。

4. アプリケーションの実行:
   アプリケーションは自動的に起動し、インタラクティブなプロンプトが表示されます。

5. 検索の実行:
   - プロンプトに従って、検索クエリを入力します。
   - 最小価格と最大価格を入力してフィルタリングします。
   - 結果が表示されます。

6. アプリケーションの終了:
   検索プロンプトで 'quit' と入力するか、Ctrl+Cを押してDocker Composeを終了します。

## 内部の動作

1. データのロード:
   - Hugging Faceの"MongoDB/airbnb_embeddings"データセットをロードします。
   - 各リスティングのデータ、埋め込み、およびアメニティ情報をRedisに保存します。

2. インデックスの作成:
   - RediSearchを使用して、複数のインデックスを作成します:
     - テキスト埋め込みに対するベクトルインデックス（FLATタイプ）
     - アメニティはカンマ区切りの文字列として保存
     - 価格に対する数値インデックス

3. 検索処理:
   - ユーザーの入力クエリに対してOpenAI APIを使用して埋め込みを生成します。
   - プレフィルタリング:
     - 指定された価格範囲でフィルタリング
   - ベクトル類似性検索を実行します。
   - ポストフィルタリング:
     - WiFi要件がある場合、アメニティリストを確認してフィルタリング

4. 結果の表示:
   - 物件の基本情報（名前、説明、価格、収容人数）
   - 類似度スコア
   - 利用可能なアメニティの一覧
   - WiFiの利用可能性を明示的に表示

## ライセンス

このプロジェクトは [MITライセンス](LICENSE) の下で公開されています。
