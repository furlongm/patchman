function repo_toggle_enabled(id, element, e) {
    e.preventDefault();
    var url = id + "toggle_enabled/";
    $.post(url);
    if (element.innerHTML.indexOf("icon-no.gif") > -1) {
        var newHTML = element.innerHTML.replace("icon-no.gif", "icon-yes.gif").replace("Disabled", "Enabled");
    } else {
        var newHTML = element.innerHTML.replace("icon-yes.gif", "icon-no.gif").replace("Enabled", "Disabled");
    }
    element.innerHTML = newHTML;
}

function repo_toggle_security(id, element, e) {
    e.preventDefault();
    var url = id + "toggle_security/";
    $.post(url);
    if (element.innerHTML.indexOf("icon-no.gif") > -1) {
        var newHTML = element.innerHTML.replace("icon-no.gif", "icon-yes.gif").replace("Non-Security", "Security");
    } else {
        var newHTML = element.innerHTML.replace("icon-yes.gif", "icon-no.gif").replace("Security", "Non-Security");
    }
    element.innerHTML = newHTML;
}
