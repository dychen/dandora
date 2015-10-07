'use strict';

var BACKGROUND_URL = 'http://www.pandora.com/static/valances/pandora/default/skin_background.jpg';

var COLORS = {
  darkblue: '#1c3f5b',
  lightblue: '#465c7d',
  brightblue: '#accdff',
};

var SPINNER = new Spinner({ color: 'white' }).spin(document.getElementById('pndra-spinner'));
SPINNER.stop();

var MainContainer = React.createClass({
  getInitialState: function() {
    return {
      currentPlaylist: '',
      /* Format: {
       *   name: [str], // Playlist name
       *   songs: [list] // List of songs titles to query on
       *   index: [int] // Index of the currently playing song
       *   maxIndex: [int] // Index of the lastest song played
       * }
       */
      playlists: [],
      /*
       * Format: {
       *   [song query]: {
       *     title: [str],
       *     artist: [str],
       *     artworkUrl: [str]
       *   },
       *   ...
       * }
       */
      songMetadata: {}
    };
  },
  getPlaylistByName: function(playlistName) {
    return this.state.playlists.filter(function(playlist) {
      return playlist.name === playlistName;
    })[0];
  },
  getPlaylistIndexByName: function(playlistName) {
    return this.state.playlists.findIndex(function(playlist) {
      return playlist.name === playlistName;
    }.bind(this));
  },
  onSearchStation: function(query, songs) {
    if (this.state.playlists.filter(function(playlist) {
      return playlist.name === query;
    }).length === 0) {
      this.setState({
        playlists: this.state.playlists.concat([{
          name: query,
          songs: songs,
          index: 0,
          maxIndex: 0
        }]),
        currentPlaylist: query
      });
    }
  },
  onFindAndPlaySong: function(query) {
    SPINNER.spin(document.getElementById('pndra-spinner'));
    $.get('/api/song', { query: query }, function(response) {
      console.log('Response', response);
      // DANGER: I think this copies by reference and we're manually mutating
      //         state (outside of this.setState())
      // See: http://stackoverflow.com/questions/518000/
      //        is-javascript-a-pass-by-reference-or-pass-by-value-language
      var newSongMetadata = this.state.songMetadata;
      newSongMetadata[query] = {
        title: response.title,
        artist: response.user,
        artworkUrl: response.artwork_url
      }
      this.setState({
        songMetadata: newSongMetadata,
        title: response.title,
        artist: response.user,
        artworkUrl: response.artwork_url
      });
      SC.stream('/tracks/' + response['id'], function(sound) {
        this.setState({ audioSrc: sound._player._descriptor.src });
        SPINNER.stop();
      }.bind(this));
    }.bind(this));
  },
  onSwitchPlaylist: function(playlistName, callback) {
    this.setState({
      currentPlaylist: playlistName
    }, function() {
      var playlist = this.getPlaylistByName(playlistName);
      callback(playlist.songs[playlist.maxIndex]);
    });
  },
  onNextSong: function(callback) {
    // React immutability helpers documentation:
    // https://facebook.github.io/react/docs/update.html
    var playlistIndex = this.getPlaylistIndexByName(this.state.currentPlaylist);
    var newPlaylists = React.addons.update(this.state.playlists, {
      [playlistIndex]: {
        maxIndex: { $set: this.state.playlists[playlistIndex].maxIndex + 1 },
        index: { $set: this.state.playlists[playlistIndex].maxIndex + 1}
      }
    });
    this.setState({
      playlists: newPlaylists
    }, function() {
      var playlist = this.getPlaylistByName(this.state.currentPlaylist);
      callback(playlist.songs[playlist.maxIndex]);
    });
  },
  onSelectSong: function(index) {
    var playlistIndex = this.getPlaylistIndexByName(this.state.currentPlaylist);
    var newPlaylists = this.state.playlists;
    newPlaylists[playlistIndex].index = index;
    this.setState({
      playlists: newPlaylists
    }, function() {
      this.onFindAndPlaySong(newPlaylists[playlistIndex].songs[index]);
    });
  },
  render: function() {
    return (
      <div id='pndra-mainContainer' className='container'>
        <TopNav />
        <SideNav playlists={this.state.playlists}
                 currentPlaylist={this.state.currentPlaylist}
                 title={this.state.title}
                 album={this.state.artist}
                 artwork={this.state.artworkUrl}
                 audioSrc={this.state.audioSrc}
                 onSearchStation={this.onSearchStation}
                 onFindAndPlaySong={this.onFindAndPlaySong}
                 onSwitchPlaylist={this.onSwitchPlaylist}
                 onNextSong={this.onNextSong} />
        <MainView playlist={this.getPlaylistByName(this.state.currentPlaylist)}
                  songMetadata={this.state.songMetadata}
                  onFindAndPlaySong={this.onFindAndPlaySong}
                  onSelectSong={this.onSelectSong} />
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
  /* NOTE: Moved all state to props */
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
  searchStation: function(item) {
    $.get('/api/playlist', { query: item }, function(response) {
      this.props.onSearchStation(item, response.data);
      this.props.onFindAndPlaySong(response.data[0]);
      $('#create-station-typeahead').text('');
    }.bind(this));
  },
  switchPlaylist: function(playlistName) {
    this.props.onSwitchPlaylist(playlistName, this.props.onFindAndPlaySong);
  },
  nextSong: function() {
    this.props.onNextSong(this.props.onFindAndPlaySong);
  },
  render: function() {
    var hidden = {
      visibility: 'hidden'
    };
    return (
      <div id='pndra-sideNav'>
        <div id='pndra-createStationInput'>
          <ReactBootstrap.Input
            id='create-station-typeahead'
            type='text'
            placeholder='Create Station'
            addonBefore={<ReactBootstrap.Glyphicon glyph='plus' />} />
        </div>

        <PlaylistList playlists={this.props.playlists}
                      currentPlaylist={this.props.currentPlaylist}
                      switchPlaylist={this.switchPlaylist} />
        <AudioPlayer audioSrc={this.props.audioSrc}
                     nextSong={this.nextSong} />

        <div id='pndra-sideNavAlbum'
          className={this.props.audioSrc ? '' : 'album-hidden'}>
          <img src={this.props.artworkUrl}></img>
          <div>{this.props.title}</div>
          <div>{this.props.artist}</div>
        </div>
      </div>
    );
  }
});

var PlaylistList = React.createClass({
  render: function() {
    return (
      <div>
        <h4>Stations</h4>
        <ul id='pndra-stationList'>
          {this.props.playlists.map(function(playlist) {
            return (
              <li onClick={this.props.switchPlaylist.bind(this, playlist.name)}
                  className={this.props.currentPlaylist === playlist.name
                             ? 'hvr hvr-grow active' : 'hvr hvr-grow'}>
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
    if (this.state.playing === true && prevState.playing === false)
      this.animationId = requestAnimationFrame(this.draw);
    // Pause animation
    else if (this.state.playing === false && prevState.playing === true)
      cancelAnimationFrame(this.animationId);
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
    this.props.nextSong();
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
      if (m < 10)
        m = '0' + m;
      return h + ':' + m + ':' + s;
    }
    return m + ':' + s;
  },
  render: function() {
    var playIcon = this.state.playing ? 'pause' : 'play';
    return (
      <div id='pndra-audioPlayerContainer'>
        <audio id='pndra-audio-player'>
        </audio>
        {this.formatTime(this.state.currentPosition)}
        &nbsp;/&nbsp;{this.formatTime(this.state.duration)}
        <ReactBootstrap.ProgressBar className='pndra-progressBar'
                                    active now={this.getProgress()} />
        <div id='pndra-audioControl'>
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph='thumbs-up' />
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph='thumbs-down' />
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph={playIcon}
                                    onClick={this.play} />
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph='fast-forward'
                                    onClick={this.handleSongEnded} />
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph='volume-up' />
        </div>
      </div>
    );
  }
});

var MainView = React.createClass({
  ALBUMWIDTH: 155, // 150 + 5px padding
  ALBUMPADDING: 50 + 15, // A bit of extra padding for buttons/right padding
  getInitialState: function() {
    return {
      scrollIndex: 0,
      maxNumAlbums: 0
    };
  },
  componentWillReceiveProps: function(newProps) {
    if (this.props.playlist
        && this.props.playlist.maxIndex !== newProps.playlist.maxIndex)
      this.setState({ scrollIndex: newProps.playlist.maxIndex });
  },
  componentDidMount: function() {
    var windowWidth = $('#pndra-albumSelect').width();
    this.setState({
      maxNumAlbums: Math.floor((windowWidth - this.ALBUMPADDING)
                                / this.ALBUMWIDTH)
    });
  },
  handleResize: function() {
    var windowWidth = $('#pndra-albumSelect').width();
    var newMaxNumAlbums = Math.floor((windowWidth - this.ALBUMPADDING)
                                     / this.ALBUMWIDTH);
    if (newMaxNumAlbums !== this.maxNumAlbums) {
      this.setState({ maxNumAlbums: newMaxNumAlbums });
    }
  },
  scrollLeft: function() {
    if (this.state.scrollIndex - this.state.maxNumAlbums + 1 > 0)
      this.setState({ scrollIndex: this.state.scrollIndex - 1 });
  },
  scrollRight: function() {
    if (this.state.scrollIndex < this.props.playlist.maxIndex)
      this.setState({ scrollIndex: this.state.scrollIndex + 1 });
  },
  render: function() {
    var albums = [];
    if (this.props.playlist) {
      var index = this.state.scrollIndex;
      var albumLength = Math.min(this.state.maxNumAlbums, index + 1);
      var songName;
      var album;
      for (var i = 0; i < albumLength; i++) {
        songName = this.props.playlist.songs[(index+1) - albumLength + i];
        if (songName in this.props.songMetadata) {
          album = this.props.songMetadata[songName];
          album.index = (index+1) - albumLength + i;
          albums.push(album);
        }
      }

      var showLeftButton = this.state.scrollIndex >= this.state.maxNumAlbums;
      var showRightButton = this.state.scrollIndex < this.props.playlist.maxIndex;
    }
    return (
      <div id='pndra-mainView'>
        <div id='pndra-albumSelect'>
          <ReactBootstrap.Button
            className='pndra-albumNav btn btn-default'
            onClick={this.scrollLeft}
            style={showLeftButton ?
                   { visibility: 'visible' } : { visibility: 'hidden' }}>
            <ReactBootstrap.Glyphicon
              className='hvr'
              glyph='chevron-left' />
          </ReactBootstrap.Button>
          <div id='pndra-albumList'>
            {albums.map(function(album, i) {
              return (
                <div className={this.props.playlist.index === album.index
                                ? 'pndra-album hvr hvr-grow selected'
                                : 'pndra-album hvr hvr-grow'}
                  onClick={this.props.onSelectSong.bind(this, album.index)}>
                  <img src={album.artworkUrl}></img>
                  <span className='albumText'>
                    <div>{album.title}</div>
                    <div>{album.artist}</div>
                  </span>
                </div>
              );
            }.bind(this))}
          </div>
          <ReactBootstrap.Button
            className='pndra-albumNav btn btn-default'
            onClick={this.scrollRight}
            style={showRightButton ?
                   { visibility: 'visible' } : { visibility: 'hidden' }}>
            <ReactBootstrap.Glyphicon
              className='hvr'
              glyph='chevron-right' />
          </ReactBootstrap.Button>
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

