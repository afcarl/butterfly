//-----------------------------------
//
// DOJO.Input - Let people control slices
// gets OpenSeadragon
// gets DOJO.Stack
// new DOJO.RealTime
//     DOJO.RealTime.init
// -- Called by main.js
// -- Init by self
//-----------------------------------

DOJO.Input = function(scope) {

    var proto = document.getElementById('proto');
    var corner = scope.openSD.element.childNodes[0].childNodes[3];
    var list = proto.getElementsByTagName("UL")[0].cloneNode(true);
    this.findings = list.getElementsByTagName("LI");
    corner.appendChild(list);
    list.id = 'findings';

    this.osd = scope.openSD;
    this.stack = scope.stack;
    this.realT = new DOJO.RealTime(scope);
    this.realT.init(this).then(this.init.bind(this));
    this.findings[0].childNodes[0].innerHTML = this.stack.now;
    this.findings[0].childNodes[1].innerHTML = '/'+this.stack.depth;
}

DOJO.Input.prototype = {

    codes: {
      190: 1,
      87: 1,
      188: 2,
      83: 2,
    },
    init: function(){
        var seaGL = this.realT.seaGL;
        var toolbar = ['home','up','down'].map(this.button, this);
        this.osd.addViewerInputHook({ keyDown: this.keyDown.bind(this, toolbar) });
        this.osd.addViewerInputHook({ clickHandler: function(e){e.quick=false;} });
        window.onkeydown = this.osd.innerTracker.keyDownHandler;
        toolbar.map(seaGL.button, seaGL);
    },
    button: function(event) {
        return {name: event, onClick: this.event.bind(this,event)};
    },
    keyDown: function(toolbar,e){
        if (e.keyCode in this.codes) {
            var index = this.codes[e.keyCode];
            toolbar[index].onClick();
            e.stopHandlers = true;
        }
    },
    event: function(event) {
        if (event == 'home'){
            window.location = 'index.html';
            return;
        }
        var level = this.stack.level;
        var check = function(slice){
            if(!slice.opacity){
              slice.setOpacity(1);
            }
            if (slice && slice.lastDrawn.length) {
                return slice.lastDrawn[0].level >= level;
            }
        }
        var slices = this.stack.check(event);
        if (slices && slices.every(check)) {
            return this[event](this.stack);
        }
    },
    up: function(stack){
        stack.now ++;
        stack.show(stack.index.up);
        stack.lose(stack.index.start);
        stack.gain(stack.zBuff, stack.index.end);
        this.findings[0].childNodes[0].innerHTML = stack.now;
    },
    down: function(stack){
        stack.now --;
        stack.show(stack.index.down);
        stack.lose(stack.index.end);
        stack.gain(-stack.zBuff, stack.index.start);
        this.findings[0].childNodes[0].innerHTML = stack.now;
    }
}