import logging
import ckan.lib.base as base
import ckan.plugins as p
import ckan.logic as logic
import ckan.model as model
import ckan.lib.captcha as captcha
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.lib.mailer as mailer
import ckan.lib.helpers as h
import socket
from pylons import config
from ckan.common import _, request, c

log = logging.getLogger(__name__)

render = base.render
abort = base.abort
redirect = base.redirect

DataError = dictization_functions.DataError
unflatten = dictization_functions.unflatten

class ContactController(base.BaseController):
    """
    Controller for displaying a contact form
    """

    def __before__(self, action, **env):

        super(ContactController, self).__before__(action, **env)

        try:
            self.context = {'model': model, 'session': model.Session, 'user': base.c.user or base.c.author, 'auth_user_obj': base.c.userobj}
            logic.check_access('site_read', self.context)
        except logic.NotAuthorized:
            base.abort(401, _('Not authorized to use contact form'))

    def _submit(self, context):

        try:
            data_dict = logic.clean_dict(unflatten(logic.tuplize_dict(logic.parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            c.form = data_dict['name']
            captcha.check_recaptcha(request)
        except logic.NotAuthorized:
            base.abort(401, _('Not authorized to see this page'))
        except captcha.CaptchaError:
            error_msg = _(u'Bad Captcha. Please try again.')
            h.flash_error(error_msg)

        errors = {}
        error_summary = {}

        if data_dict["email"] == '':
            errors['email'] = [u'Missing Value']
            error_summary['email'] = u'Missing value'

        if data_dict["name"] == '':
            errors['name'] = [u'Missing Value']
            error_summary['name'] = u'Missing value'

        if data_dict["content"] == '':
            errors['content'] = [u'Missing Value']
            error_summary['content'] = u'Missing value'

        if len(errors) == 0:
            mail_to = config.get('email_to')
            recipient_name = 'CKAN Surrey'
            subject = 'CKAN - Contact/Question from visitor'
            body = 'Submitted by %s (%s)\n' % (data_dict["name"], data_dict["email"])
            body += 'Request: %s' % data_dict["content"]

            try:
                mailer.mail_recipient(recipient_name, mail_to, subject, body)
            except (mailer.MailerException, socket.error):
                h.flash_error(_(u'Sorry, there was an error sending the email. Please try again later'))
            else:
                data_dict['success'] = True
                
        return data_dict, errors, error_summary

    def form(self):

        """
        Return a contact form
        :return: html
        """

        data = {}
        errors = {}
        error_summary = {}

        # Submit the data
        if 'save' in request.params:
            data, errors, error_summary = self._submit(self.context)
        if data.get('success', False):
            return p.toolkit.render('contact/success.html')
        else:
            vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
            return p.toolkit.render('contact/form.html', extra_vars=vars)