# Windows セットアップ手順

この文書は、縦書きXTC GUI Studio v1.2.2 を Windows で起動するための手順です。

## 1. Python を確認する

Windows のコマンドプロンプトを開き、以下を実行します。

```cmd
python --version
```

または、Python Launcher が使える環境では以下も確認します。

```cmd
py -3.12 --version
```

うまく動かない場合は、次も試してください。

```cmd
py -3.11 --version

py -3.10 --version

python --version
```

Python 3.10 / 3.11 / 3.12 のいずれかが表示されればOKです。迷った場合は Python 3.12 を推奨します。

## 2. zip を展開する

Release からダウンロードした zip を、任意の場所に展開します。

例:

```cmd
cd /d C:\Users\%USERNAME%\Downloads

tar -xf tategaki-xtc-gui-studio_v1.2.2-release.zip

cd /d C:\Users\%USERNAME%\Downloads\tategaki-xtc-gui-studio_v1.2.2-release
```

展開先フォルダ名が異なる場合は、実際のフォルダ名に合わせて移動してください。

確認:

```cmd
dir
```

`run_gui.bat`、`install_requirements.bat`、`tategakiXTC_gui_studio.py` が見えていればOKです。

## 3. 依存ライブラリをインストールする

通常は付属のバッチファイルを使います。

```cmd
install_requirements.bat
```

手動で入れる場合:

```cmd
python -m pip install --upgrade pip

python -m pip install -r requirements.txt
```

Python Launcher を使う場合:

```cmd
py -3.12 -m pip install --upgrade pip

py -3.12 -m pip install -r requirements.txt
```

## 4. 起動する

通常は以下で起動できます。

```cmd
run_gui.bat
```

手動で起動する場合:

```cmd
python -B tategakiXTC_gui_studio.py
```

Python Launcher を使う場合:

```cmd
py -3.12 -B tategakiXTC_gui_studio.py
```

## 5. 仮想環境を使う場合

環境を分けたい場合は、venv を使えます。

```cmd
py -3.12 -m venv .venv

.venv\Scripts\activate

python -m pip install --upgrade pip

python -m pip install -r requirements.txt

python -B tategakiXTC_gui_studio.py
```

次回以降は、展開先フォルダで以下を実行します。

```cmd
.venv\Scripts\activate

python -B tategakiXTC_gui_studio.py
```

## 6. よくある起動トラブル

### `python` が見つからない

Python がインストールされていない、または PATH に入っていない可能性があります。

Microsoft Store 版ではなく、公式 Python の利用を推奨します。

### `pip` でエラーになる

まず pip を更新してください。

```cmd
python -m pip install --upgrade pip
```

その後、再度 requirements をインストールします。

```cmd
python -m pip install -r requirements.txt
```

### PySide6 のインストールに時間がかかる

PySide6 はサイズが大きいため、初回インストールに時間がかかる場合があります。途中で止まっているように見えても、しばらく待ってください。

### 画面が出ない

コマンドプロンプトから手動起動し、エラーメッセージを確認してください。

```cmd
python -B tategakiXTC_gui_studio.py
```

表示されたエラー内容を控えてください。
