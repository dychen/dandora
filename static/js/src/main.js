'use strict';

var BACKGROUND_URL = 'http://www.pandora.com/static/valances/pandora/default/skin_background.jpg';

var COLORS = {
  darkblue: '#1c3f5b',
  lightblue: '#465c7d'
};

var MainContainer = React.createClass({
  getInitialState: function() {
    return {
      playlistMetadata: {}
    };
  },
  onPlaylistChange: function() {
  },
  onSongChange: function() {
  },
  render: function() {
    return (
      <div id='pndra-mainContainer' className='container'>
        <TopNav />
        <div id='pndra-bodyContainer'>
          <SideNav />
          <MainView />
        </div>
      </div>
    );
  }
});

var TopNav = React.createClass({
  render: function() {
    return (
      <div id='pndra-topNav'>
      </div>
    );
  }
});

var SideNav = React.createClass({
  getInitialState: function() {
    return {
      /* Format: {
       *   name: [str], // Playlist name
       *   songs: [list], // List of songs titles to query on
       *   index: [int] // Index of the currently playing song
       * }
       */
      playlists: [],
      currentPlaylist: null,
      title: null,
      artist: null,
      artworkUrl: null
    };
  },
  componentDidMount: function() {
    SC.initialize({
      // Sucks that this has to be initialized on the client
      client_id: '65c0de4e700c1180139971b979f997b6'
    });
    $.get('/api/songs', function(response) {
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
  getPlaylistByName: function(playlistName) {
    return this.state.playlists.filter(function(playlist) {
      return playlist.name === playlistName;
    })[0];
  },
  searchStation: function(item) {
    console.log('Searching: ', item);
    $.get('/api/playlist', { query: item }, function(response) {
      console.log(response);
      if (this.state.playlists.filter(function(playlist) {
        return playlist.name === item;
      }).length === 0) {
        this.setState({
          playlists: this.state.playlists.concat([{
            name: item,
            songs: response.data,
            index: 0
          }]),
          currentPlaylist: item
        });
        this.findAndPlaySong(response.data[0]);
      }
    }.bind(this));
  },
  findAndPlaySong: function(query) {
    $.get('/api/song', { query: query }, function(response) {
      console.log('Response', response);
      this.setState({
        title: response.title,
        artist: response.user,
        artworkUrl: response.artwork_url
      });
      SC.stream('/tracks/' + response['id'], function(sound) {
        this.setState({ audioSrc: sound._player._descriptor.src });
      }.bind(this));
    }.bind(this));
  },
  onSwitchPlaylist: function(playlistName) {
    this.setState({
      currentPlaylist: playlistName
    }, function() {
      var playlist = this.getPlaylistByName(playlistName);
      this.findAndPlaySong(playlist.songs[playlist.index]);
    });
  },
  onNextSong: function() {
    // Consider React immutability helpers:
    // https://facebook.github.io/react/docs/update.html
    var playlistIndex = this.state.playlists.findIndex(function(playlist) {
      return playlist.name === this.state.currentPlaylist;
    }.bind(this));
    // DANGER: I think this copies the reference, we we're manually mutating
    //         state
    // See: http://stackoverflow.com/questions/518000/
    //        is-javascript-a-pass-by-reference-or-pass-by-value-language
    var newPlaylists = this.state.playlists;
    newPlaylists[playlistIndex].index++;
    this.setState({
      playlists: newPlaylists
    }, function() {
      var playlist = this.getPlaylistByName(this.state.currentPlaylist);
      this.findAndPlaySong(playlist.songs[playlist.index]);
    });
  },
  render: function() {
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
    var hidden = {
      visibility: 'hidden'
    };
    return (
      <div id='pndra-sideNav'>
        <div style={inputStyle}>
          <ReactBootstrap.Input
            id='create-station-typeahead'
            type='text'
            placeholder='Create Station'
            addonBefore={<ReactBootstrap.Glyphicon glyph='plus' />} />
        </div>

        <PlaylistList playlists={this.state.playlists}
                      currentPlaylist={this.state.currentPlaylist}
                      onSwitchPlaylist={this.onSwitchPlaylist} />
        <AudioPlayer audioSrc={this.state.audioSrc}
                     onNextSong={this.onNextSong} />

        <div style={this.state.audioSrc ? songInfoStyle : hidden}>
          <img src={this.state.artworkUrl} style={albumImgStyle}></img>
          <div>{this.state.title}</div>
          <div>{this.state.artist}</div>
        </div>
      </div>
    );
  }
});

var PlaylistList = React.createClass({
  render: function() {
    var ulStyle = {
      height: 200,
      width: 250,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'left',
      justifyContent: 'flex-start',
      listStyle: 'none',
      overflow: 'scroll'
    };
    var liActive = {
      fontWeight: 'bold',
      padding: 5
    };
    var liStyle = {
      padding: 5
    };
    return (
      <div>
        <h4>Stations</h4>
        <ul style={ulStyle}>
          {this.props.playlists.map(function(playlist) {
            return (
              <li style={this.props.currentPlaylist === playlist.name
                         ? liActive : liStyle}
                  onClick={this.props.onSwitchPlaylist.bind(this, playlist.name)}
                  className='hvr hvr-grow'>
                {playlist.name}
              </li>
            );
          }.bind(this))}
        </ul>
      </div>
    );
  }
});

var AudioPlayer = React.createClass({
  getInitialState: function() {
    return {
      playing: false,
      currentPosition: 0,
      duration: 0
    };
  },
  componentDidMount: function() {
    this.audio = document.getElementById('pndra-audio-player');
    this.audio.addEventListener('timeupdate', this.handleTimeUpdate);
    this.audio.addEventListener('ended', this.handleSongEnded);
    this.audio.crossOrigin = 'anonymous';

    // Hook things up for processing:
    // MediaElementSource -> AudioContext
    this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    this.source = this.audioCtx.createMediaElementSource(this.audio);
    this.source.connect(this.audioCtx.destination);

    // Analyze waveform, hook more things up for processing:
    // MediaElementSource -> Analyser -> ScriptProcessor -> AudioContext
    this.analyser = this.audioCtx.createAnalyser();
    this.processor = this.audioCtx.createScriptProcessor(1024);
    this.source.connect(this.analyser);
    this.analyser.connect(this.processor);
    this.processor.connect(this.audioCtx.destination);

    // Initialize data buffers
    this.analyser.fftSize = 2048;

    var bufferLength = this.analyser.frequencyBinCount;
    this.timeArray = new Uint8Array(bufferLength);
    this.freqArray = new Uint8Array(bufferLength);

    this.processor.onaudioprocess = function() {
      this.analyser.getByteTimeDomainData(this.timeArray);
      this.analyser.getByteFrequencyData(this.freqArray);
    }.bind(this)

    // Prepare to draw stuff
    this.canvasLeft = document.getElementById('pndra-audioCanvasLeft');
    this.canvasLeftCtx = this.canvasLeft.getContext('2d');
    this.canvasLeftCtx.clearRect(0, 0, this.canvasLeft.width, this.canvasLeft.height);
    this.canvasRight = document.getElementById('pndra-audioCanvasRight');
    this.canvasRightCtx = this.canvasRight.getContext('2d');
    this.canvasRightCtx.clearRect(0, 0, this.canvasRight.width, this.canvasRight.height);
    this.audioDataHistorical = [];
    this.AUDIODATAWINDOWSIZE = 60 * 15; // Assuming refresh rate is 60 FPS and
                                        // we want a 30 second window
  },
  componentWillUnmount: function() {
    this.audio.removeEventListener('timeupdate');
    this.audio.removeEventListener('ended');

    this.source.disconnect();
    this.source = null;
    this.processor.onaudioprocess = function() {};
  },
  componentWillReceiveProps: function(newProps) {
    if (newProps && newProps.audioSrc && newProps.audioSrc != this.props.audioSrc) {
      this.audio.setAttribute('src', newProps.audioSrc);
      this.audio.load(); // Reload the source
      this.audio.play();
      this.setState({ playing: true });
      this.audioDataHistorical = [];
    }
  },
  componentDidUpdate: function(prevProps, prevState) {
    // Start/restart animation
    if (this.state.playing === true && prevState.playing === false) {
      this.animationId = requestAnimationFrame(this.draw);
    }
    // Pause animation
    else if (this.state.playing === false && prevState.playing === true) {
      cancelAnimationFrame(this.animationId);
      this.canvasLeftCtx.clearRect(0, 0, this.canvasLeft.width, this.canvasLeft.height);
      this.canvasRightCtx.clearRect(0, 0, this.canvasRight.width, this.canvasRight.height);
    }
  },
  drawTimeData: function() {
    var sliceWidth = this.canvasLeft.width * 1.0 / this.timeArray.length;
    this.canvasLeftCtx.lineWidth = 1;
    this.canvasLeftCtx.strokeStyle = 'rgb(255, 255, 255)';
    this.canvasLeftCtx.beginPath();
    var x = 0;
    for (var i = 0; i < this.timeArray.length; i++) {
      var dTime = this.timeArray[i] / 128.0;
      var y = dTime * this.canvasLeft.height / 2;
      if (i === 0)
        this.canvasLeftCtx.moveTo(x, y);
      else
        this.canvasLeftCtx.lineTo(x, y);
      x += sliceWidth;
    }
    this.canvasLeftCtx.lineTo(this.canvasLeft.width, this.canvasLeft.height / 2);
    this.canvasLeftCtx.stroke();
  },
  drawFreqData: function() {
    var binSize = 10;
    var barWidth = (this.canvasLeft.width / (this.freqArray.length * 3/4)) * binSize;
    var barHeight;
    var binSum;
    var x = 0;
    var gradient = this.canvasLeftCtx.createLinearGradient(0, 0, 0, this.canvasLeft.height);
    gradient.addColorStop(1, '#000066');
    gradient.addColorStop(0.8, '#000099');
    //gradient.addColorStop(0.3, '#009900');
    gradient.addColorStop(0, '#ffffff');
    this.canvasLeftCtx.fillStyle = gradient;
    for (var i = 0; i < this.freqArray.length * 3/4; i++) {
      if (i % binSize === 0) {
        barHeight = binSum / binSize;
        this.canvasLeftCtx.fillRect(x, this.canvasLeft.height-barHeight, barWidth, barHeight);
        x += barWidth;
        binSum = 0;
      }
      binSum += this.freqArray[i] / 2;
    }
  },
  drawFreqTimeseries: function() {
    var x = 0;
    var barWidth = this.canvasRight.width / this.AUDIODATAWINDOWSIZE;
    var barHeight;
    var avgFreq = 0;
    var gradient = this.canvasRightCtx.createLinearGradient(0, 0, 0, this.canvasRight.height);
    gradient.addColorStop(1, '#000066');
    gradient.addColorStop(0.8, '#000099');
    //gradient.addColorStop(0.3, '#009900');
    gradient.addColorStop(0, '#ffffff');
    this.canvasRightCtx.fillStyle = gradient;
    for (var i = 0; i < this.freqArray.length; i++) {
      avgFreq += this.freqArray[i];
    }
    avgFreq /= this.freqArray.length;
    if (this.audioDataHistorical.length === this.AUDIODATAWINDOWSIZE)
      this.audioDataHistorical.shift();
    this.audioDataHistorical.push(avgFreq);
    for (var i = 0; i < this.audioDataHistorical.length; i++) {
      barHeight = this.audioDataHistorical[i];
      this.canvasRightCtx.fillRect(x, this.canvasRight.height-barHeight, barWidth, barHeight);
      x += barWidth;
    }
  },
  draw: function() {
    this.animationId = requestAnimationFrame(this.draw);

    // Left canvas
    this.canvasLeftCtx.clearRect(0, 0, this.canvasLeft.width, this.canvasLeft.height);
    this.drawTimeData();
    this.drawFreqData();

    // Right canvas
    this.canvasRightCtx.clearRect(0, 0, this.canvasRight.width, this.canvasRight.height);
    this.drawFreqTimeseries();
  },
  handleTimeUpdate: function() {
    if (this.audio) {
      this.setState({
        currentPosition: this.audio.currentTime,
        duration: this.audio.duration
      });
    }
  },
  handleSongEnded: function() {
    this.props.onNextSong();
  },
  play: function() {
    if (this.state.playing === true)
      this.audio.pause();
    else
      this.audio.play();
    this.setState({ playing: !this.state.playing });
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
        <audio id='pndra-audio-player'>
        </audio>
        {this.formatTime(this.state.currentPosition)}/{this.formatTime(this.state.duration)}
        <ReactBootstrap.ProgressBar style={progressBarStyle} active now={this.getProgress()} />
        <div style={buttonRowStyle}>
          <ReactBootstrap.Glyphicon style={buttonStyle}
                                    className='hvr'
                                    glyph='thumbs-up' />
          <ReactBootstrap.Glyphicon style={buttonStyle}
                                    className='hvr'
                                    glyph='thumbs-down' />
          <ReactBootstrap.Glyphicon style={buttonStyle}
                                    className='hvr'
                                    glyph={playIcon}
                                    onClick={this.play} />
          <ReactBootstrap.Glyphicon style={buttonStyle}
                                    className='hvr'
                                    glyph='fast-forward'
                                    onClick={this.handleSongEnded} />
          <ReactBootstrap.Glyphicon style={buttonStyle}
                                    className='hvr'
                                    glyph='volume-up' />
        </div>
      </div>
    );
  }
});

var MainView = React.createClass({
  render: function() {
    return (
      <div id='pndra-mainView'>
        <div id='pndra-albumSelect'>
        </div>
        <span>
          <canvas id='pndra-audioCanvasLeft'>
          </canvas>
          <canvas id='pndra-audioCanvasRight'>
          </canvas>
        </span>
      </div>
    );
  }
});

React.render(React.createElement(MainContainer), document.getElementById('pndra-main'));

