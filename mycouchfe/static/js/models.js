User = Backbone.Model.extend({
    urlRoot: '/users',
    validate: function(attributes) {
        if (!attributes.username)
            return "Username not present";
        if (!attributes.first_name)
            return "First name not present";
        if (!attributes.last_name)
            return "Last name not present";
        if (!attributes.city_id)
            return "City not present";
    }
});
