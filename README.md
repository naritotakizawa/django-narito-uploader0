# django-narito-uploader0

ファイルアップローダーです。相対パスを記述しているHTMLファイルの配信等も可能です。

## 遊びかた

まずcloneします。

```
https://github.com/naritotakizawa/django-narito-uploader0
```

migrateとスーパーユーザーの作成をします。

```
python manage.py migrate
python manage.py createsuperuser
```

http://127.0.0.1:8000/admin でログインします。データの追加等はログインユーザーのみです。

http://127.0.0.1:8000 へアクセスし、ファイルのアップロードなどを楽しむ。
