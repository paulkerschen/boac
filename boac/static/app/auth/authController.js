(function(angular) {

  'use strict';

  angular.module('boac').controller('AuthController', function(authFactory, config, $scope) {

    $scope.devAuthEnabled = config.devAuthEnabled;

    $scope.devAuth = {
      uid: null,
      password: null
    };

    $scope.casLogIn = authFactory.casLogIn;

    $scope.devAuthLogIn = function() {
      return authFactory.devAuthLogIn($scope.devAuth.uid, $scope.devAuth.password);
    };

    $scope.logOut = authFactory.logOut;
  });

}(window.angular));
