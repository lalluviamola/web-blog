// fix for ie resize, from http://noteslog.com/post/how-to-fix-the-resize-event-in-ie/
( function( $ )  {
    $.fn.wresize = function( f )
    {
        version = '1.1';
        wresize = {fired: false, width: 0};
        function resizeOnce()
        {
            if ( $.browser.msie )
            {
                if ( ! wresize.fired )
                    wresize.fired = true;
                else
                {
                    var version = parseInt( $.browser.version, 10 );
                    wresize.fired = false;
                    if ( version < 7 )
                        return false;
                    else if ( version == 7 )
                    {
                        //a vertical resize is fired once, an horizontal resize twice
                        var width = $( window ).width();
                        if ( width != wresize.width )
                        {
                            wresize.width = width;
                            return false;
                        }
                    }
                }
            }
            return true;
        }
        function handleWResize( e )
        {
            if ( resizeOnce() )
                return f.apply(this, [e]);
        }
        this.each( function()
        {
            if ( this == window )
                $( this ).resize( handleWResize );
            else
                $( this ).resize( f );
        } );
        return this;
    };
} ) ( jQuery );

jQuery( function( $ )
{
    function _wnd_resize() {
        // TODO: figure out a better way to calculate the 32/68 magic constants
        var dx =  $(window).width() - 32 + 'px';
        var dy = $(window).height() - 84 + 'px';
        var note = $('textarea#note');
        note.width(dx).height(dy);
    }
    $(window).wresize( _wnd_resize );
    _wnd_resize();
} );

