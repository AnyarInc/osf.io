// You also need to load in typo.js and jquery.js
var Typo = require('typo');
// You should configure these classes.
var editor = 'editor'; // This should be the id of your editor element.
var lang = 'en_US';
var affData, dicData;

// ard-coded in the static libraries for the OSF language dictionaries
var dicPath =  '/static/dictionaries/en_US/en_US.dic';
var affPath =  '/static/dictionaries/en_US/en_US.aff';

// Make dotted red underline for gutter and words.
// Edited to conform to the OSF Style Guide
$('<style id="ace_editor_body" type="text/css">.ace_marker-layer .misspelled { position: absolute; z-index: -2; border-bottom: 1px dotted red; margin-bottom: -1px; }</style>').appendTo('head');
$('<style id="ace_editor_line_numbers" type="text/css">.misspelled { border-bottom: 1px dotted red; margin-bottom: -1px; }</style>').appendTo('head');

// Load the dictionary.
// We have to load the dictionary files sequentially to ensure
var dictionary = null ;
$.get(dicPath, function(data) {
	dicData = data;
}).done(function() {
	$.get(affPath, function(data) {
		affData = data;
	}).done(function() {
		dictionary = new Typo(lang, affData, dicData);
		enable_spellcheck();
		spell_check();
	});
});

// Check the spelling of a line, and return [start, end]-pairs for misspelled words.
function misspelled(line) {
	var words = line.split(' ');
	var i = 0;
	var bads = [];
	for (var word in words) {
		var x = words[word] + '';
		var checkWord = x.replace(/[^a-zA-Z']/g, '');
		if (!dictionary.check(checkWord)) {
			bads[bads.length] = [i, i + words[word].length];
		}
		i += words[word].length + 1;
	}
	return bads;
}

var contents_modified = true;

var currently_spellchecking = false;

var markers_present = [];

// Spell check the Ace editor contents.
function spell_check(check_right_click) {
    // Wait for the dictionary to be loaded.
	if ($('#' + editor).length) {
		if (dictionary == null) {
	        return;
	    }
	    if (currently_spellchecking) {
	    	return;
	    }

	    if (!contents_modified) {
	    	return;
	    }
	    currently_spellchecking = true;
	    var session = ace.edit(editor).getSession();

	    // Clear the markers.
	    for (var i in markers_present) {
	        session.removeMarker(markers_present[i]);
	    }
	    markers_present = [];
	    try {
		    var Range = ace.require('ace/range').Range;
		    var lines = session.getDocument().getAllLines();
		    for (var i in lines) {
		    	// Clear the gutter.
		        session.removeGutterDecoration(i, 'misspelled');
		        // Check spelling of this line.
		        var misspellings = misspelled(lines[i]);
		        // Add markers and gutter markings.
		        if (misspellings.length > 0) {
		            session.addGutterDecoration(i, 'misspelled');
		        }
		        for (var j in misspellings) {
		            var range = new Range(i, misspellings[j][0], i, misspellings[j][1]);
		            markers_present[markers_present.length] = session.addMarker(range, 'misspelled', 'typo', true);
		        }
		    }
		} finally {
			currently_spellchecking = false;
			contents_modified = false;
		}
	}
}

function enable_spellcheck() {
	if ($('#' + editor).length) {
		ace.edit(editor).getSession().on('change', function(e) {
	    	contents_modified = true;
		});
		setInterval(spell_check, 500);
	}
}
