var apiKey = 'AIzaSyBFkQBibtdyVnZ_DkIxmXCe_pOplaL0Hck';

function gmapInitialize(lat, lng) {
  var mapCanvas = $('#map_canvas');
  if (mapCanvas.length == 0) {
      return;
  }
  var latLng = new google.maps.LatLng(lat, lng);
  var mapOptions = {
    zoom: 8,
    center: latLng,
  mapTypeId: google.maps.MapTypeId.ROADMAP
  }
  var map = new google.maps.Map(document.getElementById("map_canvas"), mapOptions);
  var marker = new google.maps.Marker({
    position: latLng,
    map: map
  });
  $(mapCanvas).css('width', '220px');
  $(mapCanvas).css('height', '220px');
}

function gmapLoadScript() {
  var script = document.createElement("script");
  script.type = "text/javascript";
  script.src = "http://maps.googleapis.com/maps/api/js?key="+apiKey+"&sensor=false";
  document.body.appendChild(script);
}
