function showErrors(error_list) {
    // show errors
    for (k in error_list) {
        alert(error_list[k]);
    }
}

function serializeJSON(form) {
    // serialize JSON
    var arr = $(form).serializeArray();
    var dic = {};
    for (k in arr) {
        dic[arr[k].name] = arr[k].value;
    }
    return JSON.stringify(dic);
}

AuthView = Backbone.View.extend({
    tagName: "form",
    events: {
        "submit": "authenticate"
    },
    initialize: function() {
        //_.bindAll(this, 'render');
    },
    render: function() {
        console.get('rendered');
    },
    authenticate: function(event) {
        $.ajax('/ajax/login', {
           data: serializeJSON(this.$el),
           type: 'POST',
           contentType: 'application/json',
           cache: false,
           success: function(data, textStatus, jqXHR) {
               if (data.error_list) {
                   showErrors(data.error_list);
                   return false;
               }
               location.reload();
               return true;
           }
        });
        return false;
    }
});
var auth_view = new AuthView({ el: $("#login_form") });
