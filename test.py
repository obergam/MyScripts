def factorial(n):
    result = 1
    for x in range(n):
        result = result * n
    return result

for n in range(10):
    print(n, factorial(n))



def cube(n):
    for x in range(1,n+1):
        result = x **3
        print(result)

cube(10)


def multiple(n):
    for n in range(101):
        if 7 * n < 100:
            result = 7 * n
            print(result)


multiple(100)


