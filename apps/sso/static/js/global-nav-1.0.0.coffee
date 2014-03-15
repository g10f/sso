
###
<ul class="nav navbar-nav" id="user_apps" data-user-apps-url="#{ user-apps-url }" data-app-uuid="" data-logout-url=""></ul>
###

$ ->
	user_apps = $('#user_apps')
	if user_apps.length > 0
		user_apps_url = user_apps.data("user-apps-url")
		app_uuid = user_apps.data( "app-uuid")
		logout_url = user_apps.data("logout-url")
		add_user_apps_to_navbar(user_apps_url, app_uuid, logout_url)


get_app_item = (application, app_uuid) ->
    css_class = if (app_uuid and application.uuid is app_uuid) then "active" else ""
    return "<li class=\"#{ css_class }\"><a href=\"#{ application.links.app.href }\">#{ application.links.app.title }</a></li>";


add_thumbnail = (data) ->
    if data.picture_30x30 
        $( ".navbar i.icon-user" ).replaceWith( "<img class=\"icon-user\" height=\"30\" alt=\"\" src=\"#{data.picture_30x30}\">" )


get_text = (data, key) -> 
    if data.text and data.text[key]
        data.text[key]
    else
        key


add_user_apps_to_navbar = (user_app_url, app_uuid, logout_url) ->
    request = $.ajax(
        url: user_app_url, 
        dataType: "jsonp",
        ifModified: true,
        jsonpCallback: 'user_apps',
        cache: true)

    request.done((data) -> 
	    if data.error and data.code is 401
	        if logout_url
	           $(location).attr('href', logout_url)
	    else
	        items = []
	        applications = data.applications.filter((application) -> application.links.app.global_navigation)
	        more = get_text(data, 'More')
	        if applications.length < 4
	            $.each(applications, (idx, application) -> items.push(get_app_item(application, app_uuid)))
	        else
	            items.push(get_app_item(applications[i], app_uuid)) for i in [0..2]
	            subitems = ["<li class=\"dropdown\"><a href=\"#\" class=\"dropdown-toggle\" data-toggle=\"dropdown\">#{ more } <b class=\"caret\"></b></a><ul class=\"dropdown-menu\">"]
	            subitems.push(get_app_item(applications[i], app_uuid)) for i in [3..applications.length-1]
	            subitems.push("</ul></li>")
	            items.push(subitems.join(''))
            $('#user_apps').html(items.join(''))

            if data.links
	            if data.links.picture_30x30
	                thumbnail = "<img class=\"icon-user\" height=\"30\" alt=\"\" src=\"#{ data.links.picture_30x30.href }\">"
	            else
	                thumbnail = "<i class=\"glyphicon glyphicon-user icon-user\"></i>"
                html = "<a href=\"#{ data.links.profile.href }\">#{ thumbnail } #{ data.full_name }</a>"
                $('#user-profile').html(html)
    )
