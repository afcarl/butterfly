//-----------------------------------
//
// DOJO.Stack: Stack some tileSources
// New DOJO.Source
//     DOJO.Source.init
// -- Made by main.js
// -- Init by main.js
//-----------------------------------
log = console.log.bind(window.console);

DOJO.Stack = function(src_terms){

    // Setup
    var channels = src_terms.channel || ['i'];
    this.preset = channels.split('').map(this.layerer,this);
    this.nLayers = this.preset.length;

    // Prepare the sources
    this.protoSource = new DOJO.Source(src_terms);
    this.source = this.make(this.now, new Array(this.nLayers));
    this.index = this.indexer(this.preset,0);
    this.total = this.source.length;
}

DOJO.Stack.prototype = {
    now: 0,
    level: 0,
    zBuff: 0,
    maxBuff: 9,
    layers: {
        i: {
            set: {},
            src: {gl:0}
        },
        s: {
            set: {opacity: 0.5},
            src: {gl:0,segmentation: true}
        },
        g: {
            set: {},
            src: {gl:1,segmentation: true}
        }
    },
    layerer: function(char){
        return this.share(this.layers[char],{});
    },
    make: function(zLevel, indices) {
        return this.preset.map(this.sourcer.bind(this,zLevel,indices));
    },
    share: DOJO.Source.prototype.share.bind(null),
    sourcer: function(zLevel, indices, layer, i){
        var src = {z:zLevel,minLevel:this.level};
        var source = this.protoSource.init(this.share(layer.src, src));
        return this.share(this.share(layer.set, {index:indices[i]}), source);
    },
    indexer: function(preset,zBuff){
        var buffer = function(zb){
          return preset.map(function(p,i){
              return Math.max(zb,0)*preset.length+i;
          });
        }
        return {
          'start': buffer(0),
          'up': buffer(zBuff),
          'down': buffer(zBuff-1),
          'end': buffer(2*zBuff-1)
        }
    },
    init: function(osd){
        var w = osd.world;
        this.event = function(event){
            if (this.total == w.getItemCount()) {
              return this.index[event].map(w.getItemAt, w);
            }
        }
        this.lose = function(lost){
            lost.map(w.getItemAt,w).map(w.removeItem,w);
        }
        this.gain = function(offset, index){
            this.make(offset+this.now, index).map(osd.addTiledImage,osd);
        }
        this.show = function(shown){
            shown.map(w.getItemAt,w).map(function(shownItem){
                w.setItemIndex(shownItem, w.getItemCount()-1);
            });
            this.index.end.map(w.getItemAt,w).map(function(lastItem,i){
                w.setItemIndex(lastItem, shown[i]);
            });
        }
        this.w = w;
        return this;
    },
    updater: function(){
        if (this.zBuff < this.maxBuff){
            this.zBuff += 1;
            this.total += 2*this.nLayers;
            this.index = this.indexer(this.preset,this.zBuff);
            this.gain(-this.zBuff, this.index.start);
            this.gain(this.zBuff, this.index.end);
        }
    },
    refresher: function(e){
        e.item.addHandler('fully-loaded-change',function(e){
            var event = e.eventSource;
            var source = event.source;
            if(e.fullyLoaded){
                if(!this.w.needsDraw()){
                    this.updater();
                };
                source.minLevel = 0;
                event.draw();
                return;
            }
        }.bind(this));
    },
    zoomer: function(e){
        var z = Math.max(e.zoom,1);
        var maxLevel = this.source[0].tileSource.maxLevel;
        this.level = Math.min(Math.ceil(Math.log(z)/Math.LN2), maxLevel);
    }
};