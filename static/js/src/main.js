'use strict';

var BACKGROUND_URL = 'http://www.pandora.com/static/valances/pandora/default/skin_background.jpg';

var COLORS = {
  darkblue: '#1c3f5b',
  lightblue: '#465c7d'
};

var MainContainer = React.createClass({
  render: function() {
    var style = {
      height: '100%',
      width: '100%',
      display: 'flex',
      flexFlow: 'row wrap',
      backgroundImage: 'url(' + BACKGROUND_URL + ')',
      padding: 0
    };
    return (
      <div style={style} className='container'>
        <TopNav />
        <SideNav />
        <MainView />
      </div>
    );
  }
});

var TopNav = React.createClass({
  render: function() {
    var style = {
      height: 30,
      width: '100%',
      backgroundColor: COLORS.darkblue
    };
    return (
      <div style={style}>
      </div>
    );
  }
});

var SideNav = React.createClass({
  getInitialState: function() {
    return {
      sound: null // Sound object from SoundCloud
    };
  },
  componentDidMount: function() {
    SC.initialize({
      // Sucks that this has to be initialized on the client
      client_id: '65c0de4e700c1180139971b979f997b6'
    });
    $.get('/api/songs.json', function(response) {
      /*
       * @response: {
       *   data: ['Song1', 'Song2', 'Song3', ...]
       * }
       */
      // Make sure component is mounted. Reference:
      // https://facebook.github.io/react/tips/initial-ajax.html
      if (this.isMounted()) {
        $('#create-station-typeahead').typeahead({
          source: response.data,
          minLength: 1,
          items: 8,
          afterSelect: this.searchStation
        });
      }
    }.bind(this));
  },
  searchStation: function(item) {
    console.log('Searching: ', item);
    $.get('/api/songs', { query: item }, function(response) {
      console.log('Response', response);
      /* WARNING: Memory leak */
      SC.stream('/tracks/' + response['id'], function(sound) {
        this.setState({ sound: sound });
      }.bind(this));
    }.bind(this));
  },
  render: function() {
    var style = {
      height: '100%',
      width: 300,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'space-around',
      backgroundColor: COLORS.lightblue
    };
    var inputStyle = {
      width: 250
    };
    var songInfoStyle = {
      color: 'white',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      width: 250
    };
    var albumImgStyle = {
      height: 100,
      width: 100,
      backgroundColor: 'white'
    };
    return (
      <div style={style}>
        <div style={inputStyle}>
          <ReactBootstrap.Input
            id='create-station-typeahead'
            type='text'
            placeholder='Create Station'
            addonBefore={<ReactBootstrap.Glyphicon glyph='plus' />} />
        </div>

        <AudioPlayer player={this.state.sound} />

        <div style={songInfoStyle}>
          <div style={albumImgStyle}></div>
          <div>Piano Concerto No. 2 in C Minor</div>
          <div>Unknown</div>
          <div>Unknown</div>
        </div>
      </div>
    );
  }
});

var AudioPlayer = React.createClass({
  getInitialState: function() {
    return {
      playing: true,
      currentPosition: 0,
      duration: 0
    };
  },
  componentWillReceiveProps: function(newProps) {
    if (newProps && newProps.player) {
      // This is super sketch, but the API docs don't provide a better way to
      // do this (in particular, listening for whileplaying as documented here
      // (http://www.schillmania.com/projects/soundmanager2/doc/) doesn't work!
      // This is how they do it in the SDK code...
      newProps.player._player.bind('positionChange', this.handleTimeUpdate);
      newProps.player.play();
      this.setState({ playing: true });
    }
    if (this.props.player) {
      // Clean up
      this.props.player.stop();
      this.props.player._player.unbind('positionChange');
      // WARNING: THIS DOESN'T ACTUALLY CLEAN UP THE PREVIOUS SOUND OBJECTS!!!
      // The soundManager2 API has a way to destroy sound objects. Would be
      // nice if the SoundCloud API provided something similar...
    }
  },
  handleTimeUpdate: function() {
    if (this.props.player) {
      this.setState({
        currentPosition: this.props.player.getCurrentPosition() / 1000,
        duration: this.props.player.getDuration() / 1000
      });
    }
  },
  play: function() {
    if (this.props.player) {
      if (this.state.playing === true)
        this.props.player.pause();
      else {
        this.props.player.play();
      }
      this.setState({ playing: !this.state.playing });
    }
  },
  getProgress: function() {
    return this.state.currentPosition / this.state.duration * 100;
  },
  formatTime: function(seconds) {
    var sTotal = Math.round(seconds);
    var s = sTotal % 60;
    if (s < 10)
      s = '0' + s;
    var mTotal = Math.floor(sTotal / 60);
    var m = mTotal % 60;
    var h = Math.floor(mTotal / 60);
    if (h > 0) {
      return h + ':' + m + ':' + s;
    }
    return m + ':' + s;
  },
  render: function() {
    var buttonRowStyle = {
      display: 'flex',
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-around',
      width: 250
    };
    var buttonStyle = {
      color: 'white',
      fontSize: '2.4em',
      margin: 'auto'
    };
    var progressBarStyle = {
      width: 250
    };
    var playIcon = this.state.playing ? 'pause' : 'play';
    return (
      <div>
        <div id='pndra-audio-player'>
        </div>
        {this.formatTime(this.state.currentPosition)}/{this.formatTime(this.state.duration)}
        <ReactBootstrap.ProgressBar style={progressBarStyle} active now={this.getProgress()} />
        <div style={buttonRowStyle}>
          <ReactBootstrap.Glyphicon style={buttonStyle} glyph='thumbs-up' />
          <ReactBootstrap.Glyphicon style={buttonStyle} glyph='thumbs-down' />
          <ReactBootstrap.Glyphicon style={buttonStyle} onClick={this.play} glyph={playIcon} />
          <ReactBootstrap.Glyphicon style={buttonStyle} glyph='fast-forward' />
          <ReactBootstrap.Glyphicon style={buttonStyle} glyph='volume-up' />
        </div>
      </div>
    );
  }
});

var MainView = React.createClass({
  render: function() {
    var style = {
      height: '100%',
      flex: '1 auto'
    };
    return (
      <div style={style}>
      </div>
    );
  }
});

React.render(React.createElement(MainContainer), document.getElementById('pndra-main'));

