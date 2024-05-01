# OASST-ja Editor

[kunishou/oasst2-135k-ja](https://huggingface.co/datasets/kunishou/oasst2-135k-ja)の日本語訳テキストを手作業で修正するためのアプリです。

python 3.12.2で動作確認しています。

## Quick start

```bash
# create virtural environment (first time only)
$ python3 -m venv env
$ source env/bin/activate
# install dependencies (first time only)
(env) $ pip install -U pip setuptools
(env) $ pip install -r requirements.txt

# start the annotation app
(env) $ streamlit run annotation_app.py --browser.serverAddress localhost
```

## Edited data
編集したデータは[edited_data_flat.json](data/edited/edited_data_flat.json)に保存されます。変更は自動で保存されませんので、忘れずに`Save thread`ボタンを押すようにしてください。

アプリに表示されるデータは事前に[kunishou/oasst2-135k-ja](https://huggingface.co/datasets/kunishou/oasst2-135k-ja)から、品質の低いデータを取り除いたのものみを使っています。翻訳元のoasst2あるlabelsのデータを使って品質の低いデータをフィルタリングしています。詳しくは[こちら](notebooks/oasst2.ipynb)のnotebookを参照してください。
