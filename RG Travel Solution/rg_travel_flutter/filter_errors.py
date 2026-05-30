import sys

def filter_errors(filename):
    with open(filename, 'r', encoding='utf-16') as f:
        lines = f.readlines()
    
    errors = [line.strip() for line in lines if ' error - ' in line]
    for err in errors[:50]:
        print(err)

if __name__ == "__main__":
    filter_errors(sys.argv[1])
