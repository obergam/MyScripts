"""def is_power_of_two(n):
    # Check if the number can be divided by two without a remainder
    while n % 2 == 0 and n != 0:
        n = n / 2
    # If after dividing by two the number is 1, it's a power of two
    if n == 1:
        return True
    return False


print(is_power_of_two(0))  # Should be False
print(is_power_of_two(1))  # Should be True
print(is_power_of_two(8))  # Should be True
print(is_power_of_two(9))  # Should be False
"""
# def sum_divisors(n):
#   # Return the sum of all divisors of n, not including n
#     quotient = 1
#     result = 0
#     while quotient < n:
#         if n % quotient == 0:
#             result = result + quotient
#         quotient += 1
#     return result
#
# print(sum_divisors(6)) # Should be 1+2+3=6
# print(sum_divisors(12)) # Should be 1+2+3+4+6=16
#
# def factorial(n):
#     result = 1
#     for x in range(n):
#         result = result * n
#     return result
#
# for n in range(10):
#     print(n, factorial(n))

def cube(n):
    for x in range(1,n+1):
        result = x **3
        print(result)

cube(10)