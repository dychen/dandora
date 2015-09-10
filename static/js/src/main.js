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
      play: true
    };
  },
  play: function() {
    var mediaPlayer = document.getElementById('pndra-audio-player');
    if (this.state.play === true)
      mediaPlayer.play();
    else
      mediaPlayer.pause();
    this.setState({ play: !this.state.play });
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
    var playIcon = this.state.play ? 'play' : 'pause';
    return (
      <div style={style}>
        <div style={inputStyle}>
          <ReactBootstrap.Input
            type='text'
            placeholder='Create Station'
            addonBefore={<ReactBootstrap.Glyphicon glyph='plus' />} />
        </div>
        <audio id='pndra-audio-player'>
          <source src='../media/Rachmaninov-Piano-Concerto-2-Op-18-C-minor-1-Moderato.mp3' type='audio/mpeg' />
        </audio>
        <div style={buttonRowStyle}>
          <ReactBootstrap.Glyphicon style={buttonStyle} glyph='thumbs-up' />
          <ReactBootstrap.Glyphicon style={buttonStyle} glyph='thumbs-down' />
          <ReactBootstrap.Glyphicon style={buttonStyle} onClick={this.play} glyph={playIcon} />
          <ReactBootstrap.Glyphicon style={buttonStyle} glyph='fast-forward' />
          <ReactBootstrap.Glyphicon style={buttonStyle} glyph='volume-up' />
          <ReactBootstrap.ProgressBar active now={60} />
        </div>
        <div style={songInfoStyle}>
          <div style={albumImgStyle}></div>
          <div>Party Up (Up In Here)</div>
          <div>DMX</div>
          <div>And Then There Was X (Explicit)</div>
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

