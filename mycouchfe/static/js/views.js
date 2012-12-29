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

FormView = Backbone.View.extend({
    tagName: "form",
    events: {
        "submit": "post"
    },
    setURL: function(postURL, retURL) {
        this.postURL = '/ajax' + postURL;
        this.retURL = retURL;
        console.log(this.postURL);
    },
    post: function(event) {
        var postURL = '/ajax' + this.options.postURL;
        $.ajax(postURL, {
           data: serializeJSON(this.$el),
           retURL: this.options.retURL,
           type: 'POST',
           contentType: 'application/json',
           cache: false,
           success: function(data, textStatus, jqXHR) {
               if (data.error_list && data.error_list.length > 0) {
                   showErrors(data.error_list);
                   return false;
               }
               if (this.retURL) {
                   location.href = this.retURL;
               } else {
                   location.reload();
               }
               return true;
           }
        });
        return false;
    }
});
