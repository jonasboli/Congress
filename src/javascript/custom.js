// you can override default options globally, so they apply to every .expander() call
$.expander.defaults.slicePoint = 120;

$(document).ready(function() {
  // simple example, using all default options unless overridden globally
  $('div.expandable p').expander();

  // *** OR ***

  // override default options (also overrides global overrides)
  $('div.expandable').expander({
    slicePoint:       170,  // default is 100
    expandPrefix:     ' ', // default is '... '
    expandText:       'more', // default is 'read more'
    //collapseTimer:    5000, // re-collapses after 5 seconds; default is 0, so no re-collapsing
    userCollapseText: 'less'  // default is 'read less'
  });

});