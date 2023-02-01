# from dirg_util.dict import LDAPDict
# ldap_settings = {
#    "ldapuri": "ldaps://ldap.test.umu.se",
#    "base": "dc=umu, dc=se",
#    "filter_pattern": "(uid=%s)",
#    "user": "",
#    "passwd": "",
#    "attr": [
#        "eduPersonScopedAffiliation",
#        "eduPersonAffiliation",
#        "eduPersonPrincipalName",
#        "givenName",
#        "sn",
#        "mail",
#        "uid",
#        "o",
#        "c",
#        "labeledURI",
#        "ou",
#        "displayName",
#        "norEduPersonLIN"
#    ],
#    "keymap": {
#        "mail": "email",
#        "labeledURI": "labeledURL",
#    },
#    "static_values": {
#        "eduPersonTargetedID": "one!for!all",
#    },
#    "exact_match": True,
#    "firstonly_len1": True,
#    "timeout": 15,
# }
# Uncomment to use a LDAP directory instead.
# USERS = LDAPDict(**ldap_settings)

USERS = {
    "erik@q32.com": {
        "last_name": "Aronesty",
        "first_name": "Erik",
        "User:Email": "erik@q32.com",
    },
}

EXTRA = {
}
