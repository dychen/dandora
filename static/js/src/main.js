'use strict';

var BUCKET_URL = 'http://s3-us-west-1.amazonaws.com/pandora-s3/static/';

var SPINNER = new Spinner({ color: 'white' }).spin(document.getElementById('pndra-spinner'));
SPINNER.stop();

var MainContainer = React.createClass({
  getInitialState: function() {
    return {
      currentPlaylist: '',
      /* Format: {
       *   name: [str], // Playlist name
       *   songs: [list] // List of song metadata to query on:
       *   {
       *     id: [int],
       *     url: [str],
       *     title: [str],
       *     artist: [str],
       *     artworkUrl: [str]
       *   }
       *   index: [int] // Index of the currently playing song
       *   maxIndex: [int] // Index of the lastest song played
       * }
       */
      playlists: [],
      user: '',
      title: '',
      artist: '',
      artworkUrl: '',
      audioSrc: '',
      audio: null
    };
  },
  setIntroBlur: function() {
    var jqQueries = ['#pndra-mainContainer .background:first',
      '#pndra-mainView:first', '#pndra-sideNav-flexTop h4:first',
      '#pndra-sideNav-flexBottom:first'];
    for (var i = 0; i < jqQueries.length; i++) {
      $(jqQueries[i]).addClass('pndra-blur');
    }
    $('#pndra-createStationInput input:first').focus();
    $('#pndra-createStationPopover').css('visibility', 'visible');
  },
  unsetIntroBlur: function() {
    if ($('#pndra-createStationPopover').css('visibility') === 'visible')
      $('#pndra-createStationPopover').hide();
    var jqQueries = ['#pndra-mainContainer .background:first',
      '#pndra-mainView:first', '#pndra-sideNav-flexTop h4:first',
      '#pndra-sideNav-flexBottom:first'];
    for (var i = 0; i < jqQueries.length; i++) {
      if ($(jqQueries[i]).hasClass('pndra-blur'))
        $(jqQueries[i]).removeClass('pndra-blur');
    }
  },
  formatPlaylistResponse: function(playlistResponse) {
    var clipText = function(text, maxLen) {
      if (text.length < maxLen)
        return text;
      var textArr = text.split(' ');
      var joined = '';
      for (var i = 0; i < textArr.length; i++) {
        joined = textArr.slice(0, i+1).join(' ');
        if (joined.length > maxLen - 3)
          return textArr.slice(0, i).join(' ') + '...';
      }
      return text;
    };

    return playlistResponse.map(function(data) {
      return {
        id: data.sc_id,
        url: data.url,
        title: clipText(data.title, 50),
        artist: clipText(data.user, 25),
        artworkUrl: (data.artwork_url ? data.artwork_url
          : BUCKET_URL + 'assets/no-album.png')
      };
    });
  },
  componentDidMount: function() {
    SPINNER.spin(document.getElementById('pndra-spinner'));
    $.get('/api/user', function(response) {
      this.setState({ user: response.username });
    }.bind(this));

    var response = $.get('/api/playlists', function(response) {
      if (response.data.length > 0) {
        var formattedData = [];
        for (var i = 0; i < response.data.length; i++) {
          var formattedSongs = this.formatPlaylistResponse(response.data[i].songs);
          formattedData = formattedData.concat({
            name: response.data[i].name,
            songs: formattedSongs,
            index: 0,
            maxIndex: 0
          });
        }

        this.setState({ playlists: formattedData }, function() {
          /* If there's at least one playlist, auto-play from the first one */
          var playlistName = formattedData[0].name;
          this.onSwitchPlaylist(playlistName, this.onFindAndPlaySong)
          SPINNER.stop();
        });
      }
      else {
        this.setIntroBlur();
        SPINNER.stop();
      }
    }.bind(this));
    response.fail(function(jqXHR, textStatus, error) {
      SPINNER.stop();
      /* User isn't logged in. Do nothing. */
    });
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
    this.unsetIntroBlur();
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
    else {
      this.setState({ currentPlaylist: query });
    }
  },
  onFindAndPlaySong: function(song) {
    /*
     * @song: {
     *   id: [int],
     *   url: [str],
     *   title: [str],
     *   artist: [str],
     *   artworkUrl: [str]
     * }
     */
    SPINNER.spin(document.getElementById('pndra-spinner'));
    this.setState({
      title: song.title,
      artist: song.artist,
      artworkUrl: song.artworkUrl
    });
    SC.stream('/tracks/' + song.id, function(sound) {
      this.setState({ audioSrc: sound._player._descriptor.src });
      SPINNER.stop();
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
  onDeletePlaylist: function(playlistName) {
    SPINNER.spin(document.getElementById('pndra-spinner'));
    var request = $.ajax({
      url:'/api/playlists',
      method: 'DELETE',
      data: { name: playlistName }
    });
    request.done(function() {
      SPINNER.stop();
      // React immutability helpers documentation:
      // https://facebook.github.io/react/docs/update.html
      var playlistIndex = this.getPlaylistIndexByName(playlistName);
      var newPlaylists = React.addons.update(this.state.playlists, {
        $splice: [[playlistIndex, 1]]
      });
      this.setState({
        playlists: newPlaylists
      });
    }.bind(this));
    request.fail(function(response) {
      /* Do stuff? */
    }.bind(this));
  },
  onNextSong: function(callback) {
    // React immutability helpers documentation:
    // https://facebook.github.io/react/docs/update.html
    var playlistIndex = this.getPlaylistIndexByName(this.state.currentPlaylist);
    var playlist = this.state.playlists[playlistIndex];
    if (playlist.index === playlist.maxIndex)
      this.onNewSong(callback); // We're at the last song in the playlist, so
                                // grab a new one
    else {
      var newPlaylists = React.addons.update(this.state.playlists, {
        [playlistIndex]: {
          index: { $set: this.state.playlists[playlistIndex].index + 1}
        }
      });
      this.setState({
        playlists: newPlaylists
      }, function() {
        var playlist = this.getPlaylistByName(this.state.currentPlaylist);
        callback(playlist.songs[playlist.index]);
      });
    }
  },
  onNewSong: function(callback) {
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
        <div className='background'></div>
        <SideNav user={this.state.user}
                 playlists={this.state.playlists}
                 currentPlaylist={this.state.currentPlaylist}
                 title={this.state.title}
                 artist={this.state.artist}
                 artworkUrl={this.state.artworkUrl}
                 audioSrc={this.state.audioSrc}
                 formatPlaylistResponse={this.formatPlaylistResponse}
                 onSearchStation={this.onSearchStation}
                 onFindAndPlaySong={this.onFindAndPlaySong}
                 onSwitchPlaylist={this.onSwitchPlaylist}
                 onDeletePlaylist={this.onDeletePlaylist}
                 onNextSong={this.onNextSong}
                 onNewSong={this.onNewSong} />
        <MainView playlist={this.getPlaylistByName(this.state.currentPlaylist)}
                  audioSrc={this.state.audioSrc}
                  onFindAndPlaySong={this.onFindAndPlaySong}
                  onSelectSong={this.onSelectSong} />
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
    $.get('/api/artists', function(response) {
      /*
       * @response: {
       *   data: ['Artist1', 'Artist2', 'Artist3', ...]
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
    SPINNER.spin(document.getElementById('pndra-spinner'));
    $.post('/api/playlists', { query: item }, function(response) {
      SPINNER.stop();
      var formattedResponse = this.props.formatPlaylistResponse(response.data);
      this.props.onSearchStation(item, formattedResponse);
      this.props.onFindAndPlaySong(formattedResponse[0]);
      $('#create-station-typeahead').text('');
    }.bind(this)).fail(function(jqXHR, textStatus, error) {
      if (jqXHR.status === 409) {
        /* Play existing playlist? */
      }
    }.bind(this));
  },
  switchPlaylist: function(playlistName) {
    this.props.onSwitchPlaylist(playlistName, this.props.onFindAndPlaySong);
  },
  deletePlaylist: function(playlistName) {
    this.props.onDeletePlaylist(playlistName);
  },
  nextSong: function() {
    this.props.onNextSong(this.props.onFindAndPlaySong);
  },
  newSong: function() {
    this.props.onNewSong(this.props.onFindAndPlaySong);
  },
  login: function() {
    window.location.href = '/login';
  },
  logout: function() {
    window.location.href = '/logout';
  },
  render: function() {
    return (
      <div id='pndra-sideNav'>
        <div id='pndra-sideNav-flexTop'>
          <div id='pndra-createStationInput'>
            <ReactBootstrap.Input
              id='create-station-typeahead'
              type='text'
              placeholder='Create Station'
              addonBefore={<ReactBootstrap.Glyphicon glyph='plus' />} />
          </div>
          <ReactBootstrap.Popover
            id='pndra-createStationPopover'
            placement='right'>
            Create a station to get started!
          </ReactBootstrap.Popover>

          <h4>Stations</h4>
          <PlaylistList playlists={this.props.playlists}
                        currentPlaylist={this.props.currentPlaylist}
                        switchPlaylist={this.switchPlaylist}
                        deletePlaylist={this.deletePlaylist} />
        </div>

        <div id='pndra-sideNav-flexBottom'>
          <AudioPlayer audioSrc={this.props.audioSrc}
                       nextSong={this.nextSong}
                       newSong={this.newSong} />
          <div id='pndra-sideNavAlbum'
            className={this.props.audioSrc ? '' : 'album-hidden'}>
            <img src={this.props.artworkUrl}></img>
            <div className='albumTitle'>{this.props.title}</div>
            <div className='albumArtist'>{this.props.artist}</div>
            <hr/>
          </div>
          <span onClick={ this.props.user ? this.logout : this.login}
             id='pndra-logout' className='hvr hvr-blue'>
            { this.props.user ? this.props.user + ' (Logout)' : 'Sign In' }
          </span>
        </div>
      </div>
    );
  }
});

var PlaylistList = React.createClass({
  render: function() {
    return (
      <div>
        <ul id='pndra-stationList'>
          {this.props.playlists.map(function(playlist) {
            return (
              <li>
                <span className='pndra-deletePlaylist hvr hvr-red'
                  onClick={this.props.deletePlaylist.bind(this, playlist.name)}>
                  &#x2716;
                </span>
                <span className={this.props.currentPlaylist === playlist.name
                  ? 'pndra-playlistName hvr hvr-blue active'
                  : 'pndra-playlistName hvr hvr-blue'}
                  onClick={this.props.switchPlaylist.bind(this, playlist.name)}>
                  {playlist.name}
                </span>
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
    /* Due to CORS restrictions on AudioContext, create two audio nodes, one as
     * and AudioContext source node and another as a plain old Audio element */
    this.audioBaseNode = new Audio;
    this.audioBaseNode.setAttribute('id', 'pndra-audioPlayer-base');
    this.audioBaseNode.addEventListener('timeupdate', this.handleTimeUpdate);
    this.audioBaseNode.addEventListener('ended', this.props.nextSong);

    this.audioProcNode = new Audio;
    this.audioProcNode.setAttribute('id', 'pndra-audioPlayer-proc');
    this.audioProcNode.addEventListener('timeupdate', this.handleTimeUpdate);
    this.audioProcNode.addEventListener('ended', this.props.nextSong);
    // This allows us to access the audio context of some audio sources (in
    // particular, ones with an open Access-Control-Allow-Origin header - from
    // experience, the ec-media.sndcdn.com CDN but not the cf-media.sndcdn.com
    // CDN or ec-rtmp-media.soundcloud.com CDNs
    this.audioProcNode.setAttribute('crossOrigin', 'anonymous');

    this.audio = this.audioProcNode; // Set to processing node by default

    // CORS restrictions on AudioContext:
    // http://stackoverflow.com/questions/31895610/
    //   mediaelementaudiosource-outputs-zeroes-due-to-cors-access-restrictions-for

    // Hook things up for processing:
    // MediaElementSource -> AudioContext
    this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    this.source = this.audioCtx.createMediaElementSource(this.audioProcNode);
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
      // There should be a better way to do this (ideally, there would be a way
      // to catch "MediaElementAudioSource outputs zeroes due to CORS access
      // restrictions for [url]" errors.
      if (newProps.audioSrc.indexOf('ec-media.sndcdn.com') > -1)
        this.audio = this.audioProcNode;
      else
        this.audio = this.audioBaseNode;
      this.audioBaseNode.setAttribute('src', newProps.audioSrc);
      this.audioProcNode.setAttribute('src', newProps.audioSrc);
      this.audioBaseNode.load();
      this.audioProcNode.load();
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
    gradient.addColorStop(1, '#C1ECF7');
    gradient.addColorStop(0.5, '#1984d2');
    gradient.addColorStop(0, '#063354');
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
    gradient.addColorStop(1, '#C1ECF7');
    gradient.addColorStop(0.5, '#1984d2');
    gradient.addColorStop(0, '#063354');
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
  play: function() {
    if (this.state.playing === true)
      this.audio.pause();
    else
      this.audio.play();
    this.setState({ playing: !this.state.playing });
  },
  skipTo: function(e) {
    var ele = $('.pndra-progressBar:first');
    var xPos = e.pageX - ele.offset().left;
    var width = ele.width();
    this.audio.currentTime = this.audio.duration * (xPos / width);
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
      <div>
        {this.formatTime(this.state.currentPosition)}
        &nbsp;/&nbsp;{this.formatTime(this.state.duration)}
        <ReactBootstrap.ProgressBar className='pndra-progressBar'
                                    active now={this.getProgress()}
                                    onClick={this.skipTo} />
        <div id='pndra-audioControl'>
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph='thumbs-up' />
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph='thumbs-down' />
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph={playIcon}
                                    onClick={this.play} />
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph='step-forward'
                                    onClick={this.props.nextSong} />
          <ReactBootstrap.Glyphicon className='hvr hvr-grow pndra-audioButton'
                                    glyph='fast-forward'
                                    onClick={this.props.newSong} />
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
    if (this.props.playlist && newProps.playlist
        && this.props.playlist.maxIndex !== newProps.playlist.maxIndex)
      this.setState({ scrollIndex: newProps.playlist.maxIndex });
  },
  componentDidMount: function() {
    var windowWidth = $('#pndra-albumSelect').width();
    this.setState({
      maxNumAlbums: Math.floor((windowWidth - this.ALBUMPADDING)
                                / this.ALBUMWIDTH)
    });
    window.addEventListener('resize', this.handleResize);
  },
  componentWillUnmount: function() {
    window.removeEventListener('resize', this.handleResize);
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
      var song;
      var artworkUrl;
      for (var i = 0; i < albumLength; i++) {
        song = this.props.playlist.songs[(index+1) - albumLength + i];
        var album = {
          title: song.title,
          artist: song.artist,
          artworkUrl: song.artworkUrl,
          index: (index+1) - albumLength + i
        };
        albums.push(album);
      }

      var showLeftButton = this.state.scrollIndex >= this.state.maxNumAlbums;
      var showRightButton = this.state.scrollIndex < this.props.playlist.maxIndex;
    }
    // This is hacky (repeated in AudioPlayer component). Really should
    // abstract this to parent props.
    var showGraphs = this.props.audioSrc.indexOf('ec-media.sndcdn.com') > -1;
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
                  <div className='albumTitle'>{album.title}</div>
                  <hr/>
                  <div className='albumArtist'>{album.artist}</div>
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
          <div id='pndra-audioCanvasContainerLeft'>
            <canvas id='pndra-audioCanvasLeft'
              style={showGraphs ? {} : { display: 'none' }}>
            </canvas>
            <ReactBootstrap.Alert bsStyle='danger'
              style={!showGraphs ? {} : { display: 'none' }}>
              Unable to load audio chart.
            </ReactBootstrap.Alert>
          </div>
          <div id='pndra-audioCanvasContainerRight'>
            <canvas id='pndra-audioCanvasRight'
              style={showGraphs ? {} : { display: 'none' }}>
            </canvas>
            <ReactBootstrap.Alert bsStyle='danger'
              style={!showGraphs ? {} : { display: 'none' }}>
              Unable to load audio chart.
            </ReactBootstrap.Alert>
          </div>
        </span>
      </div>
    );
  }
});

React.render(React.createElement(MainContainer), document.getElementById('pndra-main'));

