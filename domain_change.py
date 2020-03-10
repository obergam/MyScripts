def replace_domain(email, old_domain, new_domain):
    if "@" + old_domain in email:
        index = email.index("@" + old_domain)
        print(index)
        new_email = email[:index] + "@" + new_domain
        print(new_email)
        return new_email
    return email

print(replace_domain("obergam@yahoo.com","yahoo.com","msn.com"))