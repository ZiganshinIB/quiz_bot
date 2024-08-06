import re


def main():
    data = dict()
    print('Hello World!')
    with open('temp/zoloto92.txt', 'r', encoding='KOI8-R') as f:
        quizes = f.read().split('\n\n')
        print(quizes)
    start_re_qw = r'Вопрос \d+:'
    for index, quiz in enumerate(quizes):
        check = re.search(start_re_qw, quiz)
        # Если начало совподает
        if check:
            question = re.sub(start_re_qw, '', quiz).replace('\n', ' ')
            answer = re.sub('Ответ:', "",  quizes[index+1]).replace('\n', ' ')
            data[question] = answer
    print(data)


if __name__ == '__main__':
    main()