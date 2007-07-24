/*
eggfill.c

Fill function and queue list


Copyright 2007, NATE-LSI-EPUSP

Oficina is developed in Brazil at Escola Politécnica of 
Universidade de São Paulo. NATE is part of LSI (Integrable
Systems Laboratory) and stands for Learning, Work and Entertainment
Research Group. Visit our web page: 
www.nate.lsi.usp.br
Suggestions, bugs and doubts, please email oficina@lsi.usp.br

Oficina is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License 
as published by the Free Software Foundation version 2 of 
the License.

Oficina is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with Oficina; if not, write to the
Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, 
Boston, MA  02110-1301  USA.
The copy of the GNU General Public License is found in the 
COPYING file included in the source distribution.


Authors:

Joyce Alessandra Saul               (joycealess@gmail.com)
Andre Mossinato                     (andremossinato@gmail.com)
Nathalia Sautchuk Patrício          (nathalia.sautchuk@gmail.com)
Pedro Kayatt                        (pekayatt@gmail.com)
Rafael Barbolo Lopes                (barbolo@gmail.com)
Alexandre A. Gonçalves Martinazzo   (alexandremartinazzo@gmail.com)

*/
#include <gtk/gtk.h>
#include "eggfill.h"

/*for queue*/
#define front(Q)   ( (Q)->Front )
#define rear(Q)    ( (Q)->Rear )

struct Node {
    ElementType Element;
    PtrToNode   Next;
   };

struct  QueueL{
     PtrToNode  Front;
     PtrToNode  Rear;
    } ;

/* this queue has a Header that points to the Front and Rear elements */
/* empty queue: Q->Front = NULL and Q->Rear = NULL                      */

/* check if queue Q is empty */
int IsEmpty( Queue Q ){
	return ((front(Q)==NULL) && (rear(Q)==NULL));
}
 
Queue CreateQueue( void ){
	Queue Q;
	Q = malloc ( sizeof (struct Node));
	
	/* check if there is enough space */
	if( Q == NULL )
		printf( "Out of space!!!" );
		
    front(Q) = NULL;
    rear(Q) = NULL;
    
    return Q;
}

void DisposeQueue( Queue Q ){
	MakeEmpty(Q);
	free(Q);
}

void MakeEmpty( Queue Q ){
    if( Q == NULL )
    	printf( "Must use CreateQueue first" );
	else
   		while( !IsEmpty( Q ) )
        Dequeue( Q );
}


void Enqueue( ElementType X, Queue Q ){
	PtrToNode TmpCell;
    TmpCell = malloc( sizeof( struct Node ) );
    if( TmpCell == NULL )
        printf( "Out of space!!!" );
    else {
		TmpCell->Element = X;
	    TmpCell->Next = NULL;//rear(Q);
	    if (IsEmpty(Q)){
			//printf("The Queue is empty\n");	
			front(Q)=TmpCell;
		} else rear(Q)->Next = TmpCell;
		rear(Q) = TmpCell;
    }
}


//Mostra o Elemento e 1o da Fila
ElementType Front( Queue Q ){
	if (IsEmpty(Q)){
		printf( "Empty queue" );
        return 0;  /* Return value used to avoid warning */
	} else {
    	return front(Q)->Element;
	}
}

void Dequeue( Queue Q ){
	PtrToNode tmpCell;
	tmpCell = malloc( sizeof( struct Node ) );
    if( IsEmpty( Q ) )
        printf( "Empty queue" );
    else {
		tmpCell=front(Q);
        front(Q)=front(Q)->Next;
        if (front(Q)==NULL)
			rear(Q)=NULL;
        free(tmpCell);
    }
}/* end of queue*/

void fill(GdkDrawable *drawable, GdkGC *gc, int x, int y, int width, int height, int color){

    int color_start;
    
    Queue lista_xy;
    
    lista_xy = CreateQueue();

    GdkImage *image;
    image = gdk_drawable_get_image(drawable,0,0,width,height);
    
    color_start = gdk_image_get_pixel(image, x, y);
    
    if (color!=color_start) {
        Enqueue(x, lista_xy);
        Enqueue(y, lista_xy);
        gdk_image_put_pixel(image, x, y, color);
        while (!IsEmpty(lista_xy)) {
            if (x+1 < width){
                if (gdk_image_get_pixel(image, x+1, y) == color_start){
                    gdk_image_put_pixel(image, x+1, y, color);
                    Enqueue(x+1, lista_xy);
                    Enqueue(y, lista_xy);
                }
            }
            if (x-1 >= 0){
                if (gdk_image_get_pixel(image, x-1, y) == color_start){
                    gdk_image_put_pixel(image, x-1, y, color);
                    Enqueue(x-1, lista_xy);
                    Enqueue(y, lista_xy);
                }
            }
            if (y+1 < height){
                if (gdk_image_get_pixel(image, x, y+1) == color_start){
                    gdk_image_put_pixel(image, x, y+1, color);
                    Enqueue(x, lista_xy);
                    Enqueue(y+1, lista_xy);
                }
            }
            if (y-1 >= 0){
                if (gdk_image_get_pixel(image, x, y-1) == color_start){
                    gdk_image_put_pixel(image, x, y-1, color);
                    Enqueue(x, lista_xy);
                    Enqueue(y-1, lista_xy);
                }
            }
            x = Front(lista_xy);
            Dequeue(lista_xy);
            y = Front(lista_xy);
            Dequeue(lista_xy);
       }
   }
    
   gdk_draw_image(drawable, gc, image, 0,0,0,0,width,height);

}       
