#
# def factorial(n):
#     result = 1
#     for i in range(1, n+1):
#         result = result * i
#     return result
#
# print(factorial(4)) # should return 24
# print(factorial(5)) # should return 120


# for left in range(7):
#     for right in range(left, 7):
#         print("[" + str(left) + "|" + str(right)+ "]", end=" ")
#     print()

# teams = [ 'Dragons', 'Wolves', 'Pandas', 'Unicorns']
#
# for home_team in teams:
#     for away_team in teams:
#         if home_team != away_team:
#             print(home_team + " vs " + away_team)

# def greet_friends(friends):
#     for friend in friends:
#         print("Hi " + friend)
#
# greet_friends(['Taylor', 'Louis', 'Jay', 'Adam'])
# greet_friends('Barry')
#
# def factorial(n):
# #   result = 1
# #   for x in range(n):
# #     result = result * n
# #   return result
# #
# #
# # for n in range(10):
# #   print(n, factorial(n))


# def validate_users(users):
#   for user in users:
#     if is_valid(user):
#       print(user + " is valid")
#     else:
#       print(user + " is invalid")
#
# validate_users("purplecat")
#
# def multiple(n):
#   for n in range(101):
#     if 7 * n < 100:
#       result = 7 * n
#       print(result)
#
#
# multiple(100)
# def retry(operation, attempts):
#   for n in range(attempts):
#     if operation():
#       print("Attempt " + str(n) + " succeeded")
#       break
#     else:
#       print("Attempt " + str(n) + " failed")
#
# retry(create_user, 3)
# retry(stop_service, 5)

def factorial(n):
  result = 1
  for x in range(n):
    result = n * result
    n = n - 1
  return result


for n in range(10):
  print(n, factorial(n))