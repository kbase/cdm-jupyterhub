if (!window.isSecureContext) {
  // unhide http warning
  var warning = document.getElementById('insecure-login-warning');
  if(warning){
    warning.className = warning.className.replace(/\bhidden\b/, '');
  }
}
// setup onSubmit feedback
$('form').submit((e) => {
  var form = $(e.target);
  form.find('.feedback-container>input').attr('disabled', 'true');
  form.find('.feedback-container>*').toggleClass('hidden');
  form.find('.feedback-widget>*').toggleClass('fa-pulse');
});

const enviromentOrigin = "{{ kbase_origin }}"

$('#login_not_ok').click(function () {
  window.location.href = enviromentOrigin + '/login?nextRequest=%22/cdm/redirect%22';
})

// Initial state update
updateState();
// Check for cookie changes in other windows w/ setInterval,
// in case someone goes to another window to log in
// instead of clicking through our flow.
let currentCookie = "";
setInterval(() => {
  const tokenCookie = getCookie('kbase_session');
  // if cookie changes  
  if (tokenCookie !== currentCookie) {
    if(tokenCookie) currentCookie = tokenCookie;
    updateState();
  }
}, 200);

function updateState() {
  // Check KBase token is present and valid
  checkKBaseCookie().then((username) => {
    if (username) {
      const buttonText = 'Log in with KBase as "' + username + '"';
      $('#login_submit').attr('value', buttonText);
      $('#login_submit').toggleClass('hidden', false);
      $('#login_not_ok').toggleClass('hidden', true);
    } else {
      $('#login_submit').toggleClass('hidden', true);
      $('#login_not_ok').toggleClass('hidden', false);
    }
  })
}

function checkKBaseCookie() {
  const tokenCookie = getCookie('kbase_session');
  if (!tokenCookie) return Promise.resolve(null);
  return fetch(enviromentOrigin + '/services/auth/api/V2/me', {
    headers: {
      Authorization: tokenCookie,
    },
    method: 'GET'
  }).then((resp) => {
    return resp.json();
  }).then(json => {
    if ('user' in json) {
      return json.user
    } else {
      return null;
    }
  }).catch((resp) => {
    return null;
  });
}

function getCookie(name) {
  const escapedName = name.replace(/([.*+?\^$(){}|\[\]\/\\])/g, '\\$1');
  var match = document.cookie.match(RegExp('(?:^|;\\s*)' + escapedName + '=([^;]*)'));
  return match ? match[1] : null;
}