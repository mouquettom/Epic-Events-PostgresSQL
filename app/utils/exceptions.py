class EpicEventsError(Exception):
    """ Classe mère des erreurs métier de l'application. """


class NotFoundError(EpicEventsError):
    """ La ressource demandé n'existe pas. """


class AuthorizationError(EpicEventsError):
    """ L'utilisateur n'a pas le droit d'effectuer l'action. """


class DuplicateError(EpicEventsError):
    """ Une ressource équivalente existe déjà. """


class ValidationError(EpicEventsError):
    """ Les données fournies sont invalides. """