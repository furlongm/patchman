function repo_endisable(enable, id, element) {

    if (enable == 1) {
        var url = id+"enable/";
        $.post(url, {"enable" : "true"});
        var newHTML = element.innerHTML.replace("icon-no.gif", "icon-yes.gif");
        element.innerHTML = newHTML;
        element.setAttribute('onclick', 'repo_endisable(0, '+id+', this)');
    } else {
        var url = id+"disable/";
        $.post(url, {"disable" : "true"});
        var newHTML = element.innerHTML.replace("icon-yes.gif", "icon-no.gif");
        element.innerHTML = newHTML;
        element.setAttribute('onclick', 'repo_endisable(1, '+id+', this)');
    }
}

function repo_endisablesec(enable, id, element) {

    if (enable == 1) {
        var url = id+"enablesec/";
        $.post(url, {"enablesec" : "true"});
        var newHTML = element.innerHTML.replace("icon-no.gif", "icon-yes.gif");
        element.innerHTML = newHTML;
        element.setAttribute('onclick', 'repo_endisablesec(0, '+id+', this)');
    } else {
        var url = id+"disablesec/";
        $.post(url, {"disablesec" : "true"});
        var newHTML = element.innerHTML.replace("icon-yes.gif", "icon-no.gif");
        element.innerHTML = newHTML;
        element.setAttribute('onclick', 'repo_endisablesec(1, '+id+', this)');
    }
}
