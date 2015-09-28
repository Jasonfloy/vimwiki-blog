window.click = function(){
  value = $("input").val();
  url = '/list/' + value;
  window.location.assign(url);
};

$(function(){
  url = window.location.href;
  active_id = url.split('/').pop();
  $('#'+ active_id).addClass('active')
});
