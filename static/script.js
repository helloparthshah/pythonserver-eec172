var toastElList = [].slice.call(document.querySelectorAll(".toast"));
var toastList = toastElList.map(function (toastEl) {
  return new bootstrap.Toast(toastEl, {
    animation: true,
    autohide: true,
    delay: 3000,
  });
});

let rules = [];

let iftt = function (id) {
  return `<div class="row iftt">
<div class="col text-center">IF</div>
<div class="col">
  <select onchange="changeRule('${id + "-if"}',this.value)" class="form-select">
    <option>Inside</option>
    <option>Outside</option>
  </select>
</div>
<div class="col text-center">THEN</div>
<div class="col">
<select onchange="changeRule('${id + "-then"}',this.value)" class="form-select">
    <option>Play</option>
    <option>Pause</option>
    <option>Email</option>
    <option>Text</option>
    <option>Notify</option>
</select>
</div>
<div class="col text-center">
<svg onclick="removeRule(this,'${id}')" xmlns="http://www.w3.org/2000/svg" height="40" fill="currentColor" class="bi bi-x" viewBox="0 0 16 16">
  <path d="M4.646 4.646a.5.5 0 0 1 .708 0L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 0 1 0-.708z"/>
</svg>
</div>
</div>`;
};

function removeRule(e, id) {
  e.parentNode.parentNode.remove();
  rules = rules.filter((element) => {
    return element.id != id;
  });
}

function changeRule(rule, value) {
  let id = rule.split("-")[0];
  let type = rule.split("-")[1];
  rules.forEach((element) => {
    if (element.id == id) {
      element[type] = value;
    }
  });
}

function createDiv(user) {
  let userString = JSON.stringify(user);
  return `<div id="${user.username}" class="card text-white">
  <div class="card-header">${user.username}</div>
  <div class="card-body text-center">
  <div class="rules"></div>
  <div class="buttons">
    <button
      onclick='addRule(${userString}, this)'
      type="button"
      class="btn text-white"
    >
      Add rule
    </button>
    <button
      onclick='updateRules(${userString})'
      type="button"
      class="btn text-white"
    >
      Update rules
    </button>
    </div>
  </div>
  <div class="card-footer status">
    The device is currently ${user.location == true ? "inside" : "outside"}
  </div>
</div>`;
}

function updateRules(user) {
  // get rules with username
  rule = rules.filter((element) => {
    return element.username == user.username;
  });
  $.ajax({
    url: "/updaterules",
    type: "post",
    dataType: "json",
    contentType: "application/json",
    data: JSON.stringify({
      username: user.username,
      rules: rule,
    }),
    success: function (response) {
      console.log(response);
      toastList.forEach(function (toast) {
        toast.show();
      });
    },
  });
}

$.ajax({
  url: "/getusers",
  type: "get",
  success: function (response) {
    // map users to divs
    let users = response.map((user) => {
      $.ajax({
        url: "/getrules",
        type: "post",
        dataType: "json",
        contentType: "application/json",
        data: JSON.stringify({
          username: user.username,
        }),
        success: function (response) {
          r = response.rules;
          for (let i = 0; i < r.length; i++) {
            $("#" + user.username)
              .children()[1]
              .children[0].insertAdjacentHTML(
                "beforeend",
                iftt(user.username + i)
              );
            $("#" + user.username).children()[1].children[0].children[
              i
            ].children[1].children[0].value = r[i].if_action;
            //  = r[i].if_action;
            $("#" + user.username).children()[1].children[0].children[
              i
            ].children[3].children[0].value = r[i].then_action;
            rules.push({
              id: user.username + i,
              username: user.username,
              if: r[i].if_action,
              then: r[i].then_action,
            });
          }
        },
      });
      return createDiv(user);
    });
    $("#place_for_suggestions").html(users);
  },
  error: function (xhr) {
    //Do Something to handle error
  },
});

function addRule(user, e) {
  n = e.parentNode.parentNode.children[0].children.length;
  $("#" + user.username)
    .children()[1]
    .children[0].insertAdjacentHTML("beforeend", iftt(user.username + n));
  rules.push({
    username: user.username,
    id: user.username + n,
    if: "Inside",
    then: "Play",
  });
}

function getUsers() {
  $.ajax({
    url: "/getusers",
    type: "get",
    success: function (response) {
      let $cards = $(".card");
      for (let i = 0; i < $cards.length; i++) {
        let card = $(".card:eq(" + i + ")").children();
        // find user with username 'parth'
        var user = response.find(function (u) {
          return u.username === card[0].innerText;
        });
        card[2].innerText =
          "The device is currently " +
          (user.location == true ? "inside" : "outside");
      }
    },
    error: function (xhr) {
      //Do Something to handle error
    },
  });
}

setInterval(getUsers, 1000);
