import requests
import time
from pprint import pprint
from tqdm import tqdm
import json
from datetime import datetime
# from pydrive.auth import GoogleAuth
# from pydrive.drive import GoogleDrive

class YaUploader:

    def __init__(self, token: str):
        self.token = token

    def get_headers(self):
        return {
            'Content-Type': 'application/json',
            'Authorization': 'OAuth {}'.format(self.token)
        }

    def get_status(self, operation_url):
        headers = self.get_headers()
        response = requests.get(url=operation_url, headers=headers)
        response.raise_for_status()
        status = response.json().get('status')
        if status != 'success':
            return False
        else:
            return True

    def create_folder(self, folder_name):
        url = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = self.get_headers()
        params = {'path': folder_name, 'limit': 0}
        response = requests.get(url=url, headers=headers, params=params)
        if response.status_code == 404:   # обрабатываем ошибку, если папка не найдена
            print(f'Папки {folder_name} нет, но сейчас мы её создадим!')
            response = requests.put(url=url, headers=headers, params=params)
            if response.status_code == 201:   # проверяем, что папка создалась
                print(f'Папка {folder_name} успешно создана.')
        if response.json().get('name') == folder_name:   # проверяем имя папки в метаинформации по папке
            print(f'Папка {folder_name} найдена, приступаем к загрузке.')

    def upload(self, data):
        upload_report = []
        upl_files_qty = 0
        for e in data: # обращаться здесь к списку словарей с данными по фото в качестве аргумента
            upload_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
            headers = self.get_headers()
            file_path = f'disk:/vk_photo/{e["file_name"]}'
            file_url = e['url']
            params = {'path': file_path, 'url': file_url}
            response = requests.post(upload_url, headers=headers, params=params)
            status_url = response.json()['href']
            with tqdm(total=1) as pbar:
            # хотелось, чтобы прогресс-бар заполнялся с каждой итерацией-запросом статуса,
            # но я так и не придумал, не нашел варианта, как это сделать, т.к. неизвестно,
            # сколько всего будет итераций с получением в ответе статуса in-progress
                for i in range(100):
                    time.sleep(.2)
                    self.get_status(status_url)
                    if self.get_status(status_url) == True:
                        pbar.update(1)
                        print(f'Файл {e["file_name"]} успешно загружен')
                        uploaded_file_info = {}
                        uploaded_file_info['file_name'] = e['file_name']
                        uploaded_file_info['size'] = e['size']
                        upload_report.append(uploaded_file_info)
                        upl_files_qty += 1
                        break
        print()
        print(f'Успешно загружено файлов - {upl_files_qty}')
        return upload_report

class VK:

    def __init__(self, access_token, user_id, version='5.131'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def get_photo_to_upload(self, album_id, qty=5):
        url = 'https://api.vk.com/method/photos.get'
        params = {'owner_id': self.id, 'album_id': album_id, 'photo_sizes': 1, 'extended': 1}
        response = requests.get(url, params={**self.params, **params})
        full_photo_info = response.json()['response']['items'][:qty]
        info = []
        for element in full_photo_info:
            file_info = {}
            file_info['file_name'] = '{}.jpg'.format(element['likes']['count'])
            for e in info:
                if file_info['file_name'] == e.get('file_name'):
                    # nb! если обращаться к ключам через [] - возвращается ошибка, если ключа нет
                    file_info['file_name'] = '{}'.format(element['likes']['count']) + '_{}.jpg'.format(datetime.utcfromtimestamp(element['date']).strftime('%Y-%m-%d'))
            file_info['url'] = element['sizes'][-1]['url']
            file_info['size'] = element['sizes'][-1]['type']
            file_info['date'] = element['date']
            info.append(file_info)
        return info

    def get_album_list(self):
        url = 'https://api.vk.com/method/photos.getAlbums'
        params = {'owner_id': self.id}
        response = requests.get(url, params={**self.params, **params})
        albums_list = []
        album_info = {}
        if response.json().get('error'):
            err_code = response.json().get('error').get('error_code')
            err_msg = response.json().get('error').get('error_msg')
            print(f'Что-то пошло не так! Информация об ошибке: {err_code}: {err_msg}')
            print(f'В таком случае возьмем фото профиля или со стены - это надежный вариант!')
            wall = {'album_id': 'wall', 'album_title': 'Фотографии стены'}
            profile = {'album_id': 'profile', 'album_title': 'Фотографии профиля'}
            albums_list.append(wall)
            albums_list.append(profile)
            return albums_list
        else:
            a = response.json().get('response').get('items')
            for i in a:
                album_info['album_id'] = i.get('id')
                album_info['album_title'] = i.get('title')
                albums_list.append(album_info)
            wall = {'album_id': 'wall', 'album_title': 'Фотографии стены'}
            profile = {'album_id': 'profile', 'album_title': 'Фотографии профиля'}
            albums_list.append(wall)
            albums_list.append(profile)
            return albums_list

# class GoogleUploader:

if __name__ == '__main__':
    with open('vk_token.txt') as f:
        vk_access_token = f.readline()
    user_id = int(input('Введите ID пользователя VK: '))
    with open('ya_token.txt') as f:
        ya_token = f.readline()
    vk = VK(vk_access_token, user_id)
    ya = YaUploader(ya_token)

    album_list = vk.get_album_list()

    def choose_album(lst):
        print('Список доступных папок: ')
        print()
        i = 1
        for element in album_list:
            print(f'{i} - {element.get("album_title")}')
            element.update({'iteration': i})
            i += 1
        folder_i = input('Введите номер папки, из которой необходимо загрузить фотографии: ')
        print(folder_i)
        for element in album_list:
            if element.get('iteration') == int(folder_i):
                return element.get('album_id')

    chosen_album = choose_album(album_list)

    photo_qty = int(input('Укажите количество фотографий для загрузки: '))

    data_to_upload = vk.get_photo_to_upload(album_id=chosen_album, qty=photo_qty)
    # как сделать так, чтобы аргумент qty мог быть и заданным по умолчанию?
    # если я объявляю переменную, чтобы использовать её как значение аргумента, то
    # функция уже не будет использовать значение, заданное при объявлении функции

    # pprint(data_to_upload)

    ya.create_folder('vk_photo')
    uploaded_files = ya.upload(data_to_upload)

    out_file = open("upload_info.json", "w")
    json.dump(uploaded_files, out_file, indent='')
    out_file.close()

    # можно ли добавить в словарь с параметрами каждого файла его размер в байтах и в прогресс баре
    # отслеживать загрузку по фактической загрузке файла в байтах? нужно использовать внутренняя библиотеку tqdm?