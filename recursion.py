# def sum_positive_numbers(n):
#     # The base case is n being smaller than 1
#     print("Factorial called with" + str(n))
#     if n < 1:
#         return 0
#
#     # The recursive case is adding this number to
#     # the sum of the numbers smaller than this one.
#     return n + sum_positive_numbers(n - 1)
#
# print(sum_positive_numbers(3)) # Should be 6
# print(sum_positive_numbers(5)) # Should be 15

# def is_power_of(number, base):
#   # Base case: when number is smaller than base.
#   if number < base:
#       print(str(number) + str(base))
#     # If number is equal to 1, it's a power (base**0).
#     return number == 1
#
#   # Recursive case: keep dividing number by base.
#   return is_power_of(number//base, base)
#
# print(is_power_of(8,2)) # Should be True
# print(is_power_of(64,4)) # Should be True
# print(is_power_of(70,10)) # Should be False

# def sum_positive_numbers(n):
#   if n <= 1:
#     return 1
#   return n + sum_positive_numbers(n-1)
#
# print(sum_positive_numbers(3)) # Should be 6
# print(sum_positive_numbers(5)) # Should be 15

def counter(start, stop):
    x = start
    if start > stop:
        return_string = "Counting down: "
    while x >= stop:
        return_string += str(x)
        x = x - 1
        if start != stop:
        return_string += ","
    print(return_string)
    else:
        return_string = "Counting up: "
        while x <= stop:
            return_string += str(x)
        x = x + 1
        if start != stop:
            return_string += ","
        print(return_string)
        return return_string

print(counter(1, 10))  # Should be "Counting up: 1,2,3,4,5,6,7,8,9,10"
print(counter(2, 1))  # Should be "Counting down: 2,1"
print(counter(5, 5))  # Should be "Counting up: 5"
