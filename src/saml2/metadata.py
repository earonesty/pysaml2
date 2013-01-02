#!/usr/bin/env python
from saml2.time_util import in_a_while
from saml2.extension import mdui, idpdisc, shibmd
from saml2.saml import NAME_FORMAT_URI
from saml2.attribute_converter import from_local_name
from saml2 import md
from saml2 import BINDING_HTTP_POST
from saml2 import BINDING_HTTP_REDIRECT
from saml2 import BINDING_SOAP
from saml2 import samlp
from saml2 import class_name
import xmldsig as ds

from saml2.sigver import pre_signature_part

from saml2.s_utils import factory
from saml2.s_utils import sid

__author__ = 'rolandh'

NSPAIR = {
    "saml2p":"urn:oasis:names:tc:SAML:2.0:protocol",
    "saml2":"urn:oasis:names:tc:SAML:2.0:assertion",
    "soap11":"http://schemas.xmlsoap.org/soap/envelope/",
    "meta": "urn:oasis:names:tc:SAML:2.0:metadata",
    "xsi":"http://www.w3.org/2001/XMLSchema-instance",
    "ds":"http://www.w3.org/2000/09/xmldsig#",
    "shibmd":"urn:mace:shibboleth:metadata:1.0",
    "md":"urn:oasis:names:tc:SAML:2.0:metadata",
    }

DEFAULTS = {
    "want_assertions_signed": "true",
    "authn_requests_signed": "false",
    "want_authn_requests_signed": "true",
    }

ORG_ATTR_TRANSL = {
    "organization_name": ("name", md.OrganizationName),
    "organization_display_name": ("display_name", md.OrganizationDisplayName),
    "organization_url": ("url", md.OrganizationURL)
}

def _localized_name(val, klass):
    """If no language is defined 'en' is the default"""
    try:
        (text, lang) = val
        return klass(text=text, lang=lang)
    except ValueError:
        return klass(text=val, lang="en")

def do_organization_info(ava):
    """ decription of an organization in the configuration is
    a dictionary of keys and values, where the values might be tuples:

        "organization": {
            "name": ("AB Exempel", "se"),
            "display_name": ("AB Exempel", "se"),
            "url": "http://www.example.org"
        }

    """

    if ava is None:
        return None

    org = md.Organization()
    for dkey, (ckey, klass) in ORG_ATTR_TRANSL.items():
        if ckey not in ava:
            continue
        if isinstance(ava[ckey], basestring):
            setattr(org, dkey, [_localized_name(ava[ckey], klass)])
        elif isinstance(ava[ckey], list):
            setattr(org, dkey,
                    [_localized_name(n, klass) for n in ava[ckey]])
        else:
            setattr(org, dkey, [_localized_name(ava[ckey], klass)])
    return org

def do_contact_person_info(lava):
    """ Creates a ContactPerson instance from configuration information"""

    cps = []
    if lava is None:
        return cps

    contact_person = md.ContactPerson
    for ava in lava:
        cper = md.ContactPerson()
        for (key, classpec) in contact_person.c_children.values():
            try:
                value = ava[key]
                data = []
                if isinstance(classpec, list):
                    # What if value is not a list ?
                    if isinstance(value, basestring):
                        data = [classpec[0](text=value)]
                    else:
                        for val in value:
                            data.append(classpec[0](text=val))
                else:
                    data = classpec(text=value)
                setattr(cper, key, data)
            except KeyError:
                pass
        for (prop, classpec, _) in contact_person.c_attributes.values():
            try:
                # should do a check for valid value
                setattr(cper, prop, ava[prop])
            except KeyError:
                pass

        # ContactType must have a value
        typ = getattr(cper, "contact_type")
        if not typ:
            setattr(cper, "contact_type", "technical")

        cps.append(cper)

    return cps


def do_key_descriptor(cert, use="signing"):
    return md.KeyDescriptor(
        key_info = ds.KeyInfo(
            x509_data=ds.X509Data(
                x509_certificate=ds.X509Certificate(text=cert)
            )
        ),
        use=use
    )

def do_requested_attribute(attributes, acs, is_required="false"):
    lista = []
    for attr in attributes:
        attr = from_local_name(acs, attr, NAME_FORMAT_URI)
        args = {}
        for key in attr.keyswv():
            args[key] = getattr(attr, key)
        args["is_required"] = is_required
        args["name_format"] = NAME_FORMAT_URI
        lista.append(md.RequestedAttribute(**args))
    return lista

def do_uiinfo(_uiinfo):
    uii = mdui.UIInfo()
    for attr in ['display_name', 'description', "information_url",
                 'privacy_statement_url']:
        try:
            val = _uiinfo[attr]
        except KeyError:
            continue

        aclass = uii.child_class(attr)
        inst = getattr(uii, attr)
        if isinstance(val, basestring):
            ainst = aclass(text=val)
            inst.append(ainst)
        elif isinstance(val, dict):
            ainst = aclass()
            ainst.text = val["text"]
            ainst.lang = val["lang"]
            inst.append(ainst)
        else :
            for value in val:
                if isinstance(value, basestring):
                    ainst = aclass(text=value)
                    inst.append(ainst)
                elif isinstance(value, dict):
                    ainst = aclass()
                    ainst.text = value["text"]
                    ainst.lang = value["lang"]
                    inst.append(ainst)

    try:
        _attr = "logo"
        val = _uiinfo[_attr]
        inst = getattr(uii, _attr)
        # dictionary or list of dictionaries
        if isinstance(val, dict):
            logo = mdui.Logo()
            for attr, value in val.items():
                if attr in logo.keys():
                    setattr(logo, attr, value)
            inst.append(logo)
        elif isinstance(val, list):
            for logga in val:
                if not isinstance(logga, dict):
                    raise Exception("Configuration error !!")
                logo = mdui.Logo()
                for attr, value in logga.items():
                    if attr in logo.keys():
                        setattr(logo, attr, value)
                inst.append(logo)
    except KeyError:
        pass

    try:
        _attr = "keywords"
        val = _uiinfo[_attr]
        inst = getattr(uii, _attr)
        # list of basestrings, dictionary or list of dictionaries
        if isinstance(val, list):
            for value in val:
                keyw = mdui.Keywords()
                if isinstance(value, basestring):
                    keyw.text = " ".join(value)
                elif isinstance(value, dict):
                    keyw.text = " ".join(value["text"])
                    try:
                        keyw.lang = value["lang"]
                    except KeyError:
                        pass
                else:
                    raise Exception("Configuration error: ui_info logo")
                inst.append(keyw)
        elif isinstance(val, dict):
            keyw = mdui.Keywords()
            keyw.text = " ".join(val["text"])
            try:
                keyw.lang = val["lang"]
            except KeyError:
                pass
            inst.append(keyw)
        else:
            raise Exception("Configuration Error: ui_info logo")
    except KeyError:
        pass

    return uii

def do_idpdisc(discovery_response):
    return idpdisc.DiscoveryResponse(index="0", location=discovery_response,
                                     binding=idpdisc.NAMESPACE)

ENDPOINTS = {
    "sp": {
        "artifact_resolution_service": (md.ArtifactResolutionService, True),
        "single_logout_service": (md.SingleLogoutService, False),
        "manage_name_id_service": (md.ManageNameIDService, False),
        "assertion_consumer_service": (md.AssertionConsumerService, True),
        },
    "idp":{
        "artifact_resolution_service": (md.ArtifactResolutionService, True),
        "single_logout_service": (md.SingleLogoutService, False),
        "manage_name_id_service": (md.ManageNameIDService, False),
        "single_sign_on_service": (md.SingleSignOnService, False),
        "name_id_mapping_service": (md.NameIDMappingService, False),
        "assertion_id_request_service": (md.AssertionIDRequestService, False),
        },
    "aa":{
        "artifact_resolution_service": (md.ArtifactResolutionService, True),
        "single_logout_service": (md.SingleLogoutService, False),
        "manage_name_id_service": (md.ManageNameIDService, False),

        "assertion_id_request_service": (md.AssertionIDRequestService, False),

        "attribute_service": (md.AttributeService, False)
    },
    "pdp": {
        "authz_service": (md.AuthzService, True)
    }
}

DEFAULT_BINDING = {
    "assertion_consumer_service": BINDING_HTTP_POST,
    "single_sign_on_service": BINDING_HTTP_REDIRECT,
    "single_logout_service": BINDING_HTTP_POST,
    "attribute_service": BINDING_SOAP,
    "artifact_resolution_service": BINDING_SOAP
}

def do_endpoints(conf, endpoints):
    service = {}

    for endpoint, (eclass, indexed) in endpoints.items():
        try:
            servs = []
            i = 1
            for args in conf[endpoint]:
                if isinstance(args, basestring): # Assume it's the location
                    args = {"location":args,
                            "binding": DEFAULT_BINDING[endpoint]}
                elif isinstance(args, tuple): # (location, binding)
                    args = {"location":args[0], "binding": args[1]}
                if indexed and "index" not in args:
                    args["index"] = "%d" % i
                servs.append(factory(eclass, **args))
                i += 1
                service[endpoint] = servs
        except KeyError:
            pass
    return service

DEFAULT = {
    "want_assertions_signed": "true",
    "authn_requests_signed": "false",
    "want_authn_requests_signed": "false",
    }

def do_spsso_descriptor(conf, cert=None):
    spsso = md.SPSSODescriptor()
    spsso.protocol_support_enumeration = samlp.NAMESPACE

    endps = conf.getattr("endpoints", "sp")
    if endps:
        for (endpoint, instlist) in do_endpoints(endps,
                                                 ENDPOINTS["sp"]).items():
            setattr(spsso, endpoint, instlist)

    if cert:
        spsso.key_descriptor = do_key_descriptor(cert)

    for key in ["want_assertions_signed", "authn_requests_signed"]:
        try:
            val = conf.getattr(key, "sp")
            if val is None:
                setattr(spsso, key, DEFAULT[key]) #default ?!
            else:
                strval = "{0:>s}".format(val)
                setattr(spsso, key, strval.lower())
        except KeyError:
            setattr(spsso, key, DEFAULTS[key])

    requested_attributes = []
    acs = conf.attribute_converters
    req = conf.getattr("required_attributes", "sp")
    if req:
        requested_attributes.extend(do_requested_attribute(req, acs,
                                                           is_required="true"))

    opt=conf.getattr("optional_attributes", "sp")
    if opt:
        requested_attributes.extend(do_requested_attribute(opt, acs))

    if requested_attributes:
        spsso.attribute_consuming_service = [md.AttributeConsumingService(
            requested_attribute=requested_attributes,
            service_name= [md.ServiceName(lang="en",text=conf.name)],
            index="1",
            )]
        try:
            if conf.description:
                try:
                    (text, lang) = conf.description
                except ValueError:
                    text = conf.description
                    lang = "en"
                spsso.attribute_consuming_service[0].service_description = [
                    md.ServiceDescription(text=text,
                                          lang=lang)]
        except KeyError:
            pass

    dresp = conf.getattr("discovery_response", "sp")
    if dresp:
        if spsso.extensions is None:
            spsso.extensions = md.Extensions()
        spsso.extensions.add_extension_element(do_idpdisc(dresp))

    return spsso

def do_idpsso_descriptor(conf, cert=None):
    idpsso = md.IDPSSODescriptor()
    idpsso.protocol_support_enumeration = samlp.NAMESPACE

    endps = conf.getattr("endpoints", "idp")
    if endps:
        for (endpoint, instlist) in do_endpoints(endps,
                                                 ENDPOINTS["idp"]).items():
            setattr(idpsso, endpoint, instlist)

    scopes = conf.getattr("scope", "idp")
    if scopes:
        if idpsso.extensions is None:
            idpsso.extensions = md.Extensions()
        for scope in scopes:
            mdscope = shibmd.Scope()
            mdscope.text = scope
            # unless scope contains '*'/'+'/'?' assume non regexp ?
            mdscope.regexp = "false"
            idpsso.extensions.add_extension_element(mdscope)

    ui_info = conf.getattr("ui_info", "idp")
    if ui_info:
        if idpsso.extensions is None:
            idpsso.extensions = md.Extensions()
        idpsso.extensions.add_extension_element(do_uiinfo(ui_info))

    if cert:
        idpsso.key_descriptor = do_key_descriptor(cert)

    for key in ["want_authn_requests_signed"]:
        try:
            val = conf.getattr(key, "idp")
            if val is None:
                setattr(idpsso, key, DEFAULT["want_authn_requests_signed"])
            else:
                setattr(idpsso, key, "%s" % val)
        except KeyError:
            setattr(idpsso, key, DEFAULTS[key])

    return idpsso

def do_aa_descriptor(conf, cert):
    aad = md.AttributeAuthorityDescriptor()
    aad.protocol_support_enumeration = samlp.NAMESPACE

    endps = conf.getattr("endpoints", "aa")

    if endps:
        for (endpoint, instlist) in do_endpoints(endps,
                                                 ENDPOINTS["aa"]).items():
            setattr(aad, endpoint, instlist)

    if cert:
        aad.key_descriptor = do_key_descriptor(cert)

    return aad

def do_pdp_descriptor(conf, cert):
    """ Create a Policy Decision Point descriptor """
    pdp = md.PDPDescriptor()

    pdp.protocol_support_enumeration = samlp.NAMESPACE

    endps = conf.getattr("endpoints", "pdp")

    if endps:
        for (endpoint, instlist) in do_endpoints(endps,
                                                 ENDPOINTS["pdp"]).items():
            setattr(pdp, endpoint, instlist)

    namef = conf.getattr("name_form", "pdp")
    if namef:
        if isinstance(namef, basestring):
            ids = [md.NameIDFormat(namef)]
        else:
            ids = [md.NameIDFormat(text=form) for form in namef]
        setattr(pdp, "name_id_format", ids)

    if cert:
        pdp.key_descriptor = do_key_descriptor(cert)

    return pdp

def entity_descriptor(confd):
    mycert = "".join(open(confd.cert_file).readlines()[1:-1])

    entd = md.EntityDescriptor()
    entd.entity_id = confd.entityid

    if confd.valid_for:
        entd.valid_until = in_a_while(hours=int(confd.valid_for))

    if confd.organization is not None:
        entd.organization = do_organization_info(confd.organization)
    if confd.contact_person is not None:
        entd.contact_person = do_contact_person_info(confd.contact_person)

    serves = confd.serves
    if not serves:
        raise Exception(
            'No service type ("sp","idp","aa") provided in the configuration')

    if "sp" in serves:
        confd.context = "sp"
        entd.spsso_descriptor = do_spsso_descriptor(confd, mycert)
    if "idp" in serves:
        confd.context = "idp"
        entd.idpsso_descriptor = do_idpsso_descriptor(confd, mycert)
    if "aa" in serves:
        confd.context = "aa"
        entd.attribute_authority_descriptor = do_aa_descriptor(confd, mycert)
    if "pdp" in serves:
        confd.context = "pdp"
        entd.pdp_descriptor = do_pdp_descriptor(confd, mycert)

    return entd

def entities_descriptor(eds, valid_for, name, ident, sign, secc):
    entities = md.EntitiesDescriptor(entity_descriptor= eds)
    if valid_for:
        entities.valid_until = in_a_while(hours=valid_for)
    if name:
        entities.name = name
    if ident:
        entities.id = ident

    if sign:
        if not ident:
            ident = sid()

        if not secc.key_file:
            raise Exception("If you want to do signing you should define " +
                            "a key to sign with")

        if not secc.my_cert:
            raise Exception("If you want to do signing you should define " +
                            "where your public key are")

        entities.signature = pre_signature_part(ident, secc.my_cert, 1)
        entities.id = ident
        xmldoc = secc.sign_statement_using_xmlsec("%s" % entities,
                                                  class_name(entities))
        entities = md.entities_descriptor_from_string(xmldoc)
    return entities

def sign_entity_descriptor(edesc, ident, secc):
    if not ident:
        ident = sid()

    edesc.signature = pre_signature_part(ident, secc.my_cert, 1)
    edesc.id = ident
    xmldoc = secc.sign_statement_using_xmlsec("%s" % edesc, class_name(edesc))
    return md.entity_descriptor_from_string(xmldoc)